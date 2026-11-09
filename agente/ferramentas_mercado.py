"""Ferramentas de dados do mercado financeiro para os agentes.

Fontes gratuitas, sem chave de API:
- Yahoo Finance (yfinance): ações e FIIs da B3 (sufixo .SA), BDRs, índices,
  câmbio, cripto e commodities.
- Banco Central do Brasil, SGS (api.bcb.gov.br): Selic, CDI, IPCA e dólar PTAX.

Todas as ferramentas devolvem JSON compacto, para caber no limite de
tokens do modelo, e nunca levantam exceção: em caso de falha retornam
{"erro": "..."} para o agente poder seguir.
"""

import json
import re
import urllib.request
from typing import Any

from agno.tools import Toolkit

# Séries do SGS/BCB
SERIES_BCB = {
    "selic_meta_aa": (432, "Taxa Selic meta (% a.a.)"),
    "cdi_aa": (4389, "CDI anualizado base 252 (% a.a.)"),
    "ipca_12m": (13522, "IPCA acumulado em 12 meses (%)"),
    "dolar_ptax": (1, "Dólar PTAX venda (R$)"),
}

# Apelidos aceitos -> ticker do Yahoo Finance
APELIDOS = {
    "IBOV": "^BVSP",
    "IBOVESPA": "^BVSP",
    "DOLAR": "BRL=X",
    "DÓLAR": "BRL=X",
    "USDBRL": "BRL=X",
    "EURO": "EURBRL=X",
    "EURBRL": "EURBRL=X",
    "SP500": "^GSPC",
    "S&P500": "^GSPC",
    "NASDAQ": "^IXIC",
    "DOWJONES": "^DJI",
    "BITCOIN": "BTC-USD",
    "BTC": "BTC-USD",
    "ETHEREUM": "ETH-USD",
    "ETH": "ETH-USD",
    "OURO": "GC=F",
    "PETROLEO": "BZ=F",
    "PETRÓLEO": "BZ=F",
    "BRENT": "BZ=F",
}

PANORAMA = {
    "Ibovespa": "^BVSP",
    "Dólar (R$)": "BRL=X",
    "S&P 500": "^GSPC",
    "Nasdaq": "^IXIC",
    "Bitcoin (US$)": "BTC-USD",
    "Petróleo Brent (US$)": "BZ=F",
}

# Ações, units, FIIs e BDRs da B3: 4 letras + 1-2 dígitos (PETR4, TAEE11, MXRF11, AAPL34)
_PADRAO_B3 = re.compile(r"^[A-Z]{4}\d{1,2}[A-Z]?$")

# Tabela regressiva do IR para renda fixa (dias corridos -> alíquota)
TABELA_IR = ((180, 0.225), (360, 0.20), (720, 0.175), (float("inf"), 0.15))


# ---------------------------------------------------------------------------
# Funções puras
# ---------------------------------------------------------------------------

def normalizar_ticker(ticker: str) -> str:
    """'petr4' -> 'PETR4.SA'; 'ibov' -> '^BVSP'; 'AAPL' -> 'AAPL'."""
    t = ticker.strip().upper().replace(" ", "")
    if t in APELIDOS:
        return APELIDOS[t]
    if _PADRAO_B3.match(t):
        return f"{t}.SA"
    return t


def aliquota_ir(dias: int) -> float:
    for limite, aliquota in TABELA_IR:
        if dias <= limite:
            return aliquota
    return TABELA_IR[-1][1]  # pragma: no cover


def simular_renda_fixa(valor: float, taxa_anual_pct: float, meses: int, isento_ir: bool = False) -> dict:
    """Simula juros compostos com IR regressivo (CDB, Tesouro) ou isento (LCI/LCA)."""
    if valor <= 0 or meses <= 0:
        raise ValueError("valor e meses devem ser positivos")
    fator = (1 + taxa_anual_pct / 100) ** (meses / 12)
    bruto = valor * fator
    rendimento = bruto - valor
    dias = meses * 30
    aliquota = 0.0 if isento_ir else aliquota_ir(dias)
    imposto = rendimento * aliquota
    liquido = bruto - imposto
    return {
        "valor_investido": round(valor, 2),
        "taxa_anual_pct": taxa_anual_pct,
        "meses": meses,
        "valor_bruto": round(bruto, 2),
        "rendimento_bruto": round(rendimento, 2),
        "aliquota_ir_pct": round(aliquota * 100, 1),
        "imposto_renda": round(imposto, 2),
        "valor_liquido": round(liquido, 2),
        "rentabilidade_liquida_pct": round((liquido / valor - 1) * 100, 2),
    }


def _variacao(atual: float, anterior: float) -> float | None:
    if not anterior:
        return None
    return round((atual / anterior - 1) * 100, 2)


def resumir_historico(fechamentos: list[float]) -> dict:
    """Resume uma série de fechamentos diários (mais antigo -> mais recente)."""
    if not fechamentos:
        raise ValueError("sem dados de preço")
    atual = fechamentos[-1]

    def ha(n: int) -> float | None:
        return fechamentos[-1 - n] if len(fechamentos) > n else None

    return {
        "preco": round(atual, 2),
        "variacao_dia_pct": _variacao(atual, ha(1)),
        "variacao_mes_pct": _variacao(atual, ha(21)),
        "variacao_12m_pct": _variacao(atual, fechamentos[0]) if len(fechamentos) > 200 else None,
        "maxima_periodo": round(max(fechamentos), 2),
        "minima_periodo": round(min(fechamentos), 2),
    }


# ---------------------------------------------------------------------------
# Acesso a dados (isolado para facilitar testes)
# ---------------------------------------------------------------------------

def _historico(ticker_yahoo: str, periodo: str = "1y") -> list[float]:
    import yfinance as yf  # import tardio: só quando a ferramenta é usada

    dados = yf.Ticker(ticker_yahoo).history(period=periodo, auto_adjust=False)
    if dados is None or dados.empty:
        return []
    return [float(v) for v in dados["Close"].dropna().tolist()]


def _moeda(ticker_yahoo: str) -> str:
    if ticker_yahoo.endswith(".SA") or ticker_yahoo in ("^BVSP", "BRL=X", "EURBRL=X"):
        return "BRL"
    return "USD"


def _buscar_serie_bcb(codigo: int) -> dict:
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados/ultimos/1?formato=json"
    req = urllib.request.Request(url, headers={"User-Agent": "news-analytics-platform"})
    with urllib.request.urlopen(req, timeout=15) as resposta:
        dado = json.load(resposta)[-1]
    return {"valor": float(dado["valor"]), "data": dado["data"]}


# ---------------------------------------------------------------------------
# Funções de alto nível (usadas pelas ferramentas e pela UI)
# ---------------------------------------------------------------------------

def obter_cotacao(ticker: str) -> dict:
    ticker_yahoo = normalizar_ticker(ticker)
    try:
        resumo = resumir_historico(_historico(ticker_yahoo, "1y"))
    except Exception as erro:  # noqa: BLE001
        return {"ticker": ticker_yahoo, "erro": f"cotação indisponível: {erro}"}
    return {"ticker": ticker_yahoo, "moeda": _moeda(ticker_yahoo), **resumo, "fonte": "Yahoo Finance"}


def obter_indicadores() -> dict:
    indicadores: dict[str, Any] = {}
    for chave, (codigo, descricao) in SERIES_BCB.items():
        try:
            indicadores[chave] = {"descricao": descricao, **_buscar_serie_bcb(codigo)}
        except Exception as erro:  # noqa: BLE001
            indicadores[chave] = {"descricao": descricao, "erro": str(erro)}
    indicadores["fonte"] = "Banco Central do Brasil (SGS)"
    return indicadores


def obter_panorama() -> dict:
    panorama = {}
    for nome, ticker in PANORAMA.items():
        cotacao = obter_cotacao(ticker)
        panorama[nome] = {
            k: cotacao.get(k) for k in ("ticker", "preco", "variacao_dia_pct", "erro") if cotacao.get(k) is not None
        }
    return panorama


# ---------------------------------------------------------------------------
# Toolkit para os agentes
# ---------------------------------------------------------------------------

def _json(dados: Any) -> str:
    return json.dumps(dados, ensure_ascii=False)


class MercadoFinanceiroTools(Toolkit):
    """Cotações, indicadores econômicos e simulações para o analista de investimentos."""

    def __init__(self, **kwargs):
        super().__init__(
            name="mercado_financeiro",
            tools=[
                self.cotacao_ativo,
                self.indicadores_economicos,
                self.panorama_mercado,
                self.simular_investimento_renda_fixa,
            ],
            **kwargs,
        )

    def cotacao_ativo(self, ticker: str) -> str:
        """Cotação atual e variações (dia, mês, 12 meses) de um ativo.

        Args:
            ticker: Código do ativo. Ações/FIIs/BDRs da B3 sem sufixo (PETR4, VALE3,
                MXRF11, AAPL34), ações dos EUA (AAPL, NVDA) ou apelidos: IBOV, DOLAR,
                EURO, SP500, NASDAQ, BITCOIN, ETH, OURO, BRENT.

        Returns:
            JSON com preço, moeda, variações percentuais e máxima/mínima de 12 meses.
        """
        return _json(obter_cotacao(ticker))

    def indicadores_economicos(self) -> str:
        """Indicadores oficiais do Banco Central: Selic meta, CDI, IPCA 12 meses e dólar PTAX.

        Returns:
            JSON com valor e data de referência de cada indicador.
        """
        return _json(obter_indicadores())

    def panorama_mercado(self) -> str:
        """Visão geral do dia: Ibovespa, dólar, S&P 500, Nasdaq, Bitcoin e petróleo Brent.

        Returns:
            JSON com preço e variação do dia de cada referência.
        """
        return _json(obter_panorama())

    def simular_investimento_renda_fixa(
        self, valor: float, taxa_anual_pct: float, meses: int, isento_ir: bool = False
    ) -> str:
        """Simula um investimento de renda fixa com juros compostos e IR regressivo.

        Args:
            valor: Valor investido em reais.
            taxa_anual_pct: Taxa anual em % (ex.: 13.65 para 100% do CDI atual).
            meses: Prazo em meses.
            isento_ir: True para LCI/LCA/CRI/CRA (isentos de IR para pessoa física).

        Returns:
            JSON com valor bruto, imposto, valor líquido e rentabilidade líquida.
        """
        try:
            return _json(simular_renda_fixa(valor, taxa_anual_pct, meses, isento_ir))
        except ValueError as erro:
            return _json({"erro": str(erro)})
