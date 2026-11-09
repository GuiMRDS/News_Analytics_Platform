"""Ferramentas de dados do mercado financeiro para os agentes.

Fontes gratuitas, sem chave de API:
- Yahoo Finance (API pública de gráficos, endpoints spark/chart): ações e FIIs
  da B3 (sufixo .SA), BDRs, índices, câmbio, cripto e commodities.
- Banco Central do Brasil, SGS (api.bcb.gov.br): Selic, CDI, IPCA e dólar PTAX.

Todas as ferramentas devolvem JSON compacto, para caber no limite de
tokens do modelo, e nunca levantam exceção: em caso de falha retornam
{"erro": "..."} para o agente poder seguir.
"""

import json
import re
import threading
import urllib.parse
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

# API pública de gráficos do Yahoo Finance. Chamada direta (sem yfinance): o
# yfinance busca um cookie/crumb que costuma dar timeout e somar ~30 s por
# consulta; os endpoints abaixo respondem em < 0,5 s e não exigem cookie.
YAHOO_SPARK = "https://query1.finance.yahoo.com/v8/finance/spark"
YAHOO_CHART = "https://query2.finance.yahoo.com/v8/finance/chart/"
MAX_SIMBOLOS_SPARK = 20
_limite_yahoo = threading.BoundedSemaphore(4)  # evita rajadas que derrubam o DNS/geram bloqueio


def _yahoo_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (news-analytics-platform)", "Accept": "application/json"})
    with _limite_yahoo, urllib.request.urlopen(req, timeout=12) as resposta:
        return json.load(resposta)


def _historicos_lote(tickers_yahoo: list[str], periodo: str = "1y") -> dict[str, list[float]]:
    """Fechamentos diários de vários ativos em poucas requisições (endpoint spark)."""
    resultado: dict[str, list[float]] = {}
    for i in range(0, len(tickers_yahoo), MAX_SIMBOLOS_SPARK):
        lote = tickers_yahoo[i:i + MAX_SIMBOLOS_SPARK]
        simbolos = urllib.parse.quote(",".join(lote), safe=",")
        dados = _yahoo_json(f"{YAHOO_SPARK}?symbols={simbolos}&range={periodo}&interval=1d")
        for simbolo, serie in (dados or {}).items():
            fechamentos = (serie or {}).get("close") or []
            resultado[simbolo] = [float(v) for v in fechamentos if v is not None]
    return resultado


def _historico(ticker_yahoo: str, periodo: str = "1y") -> list[float]:
    return _historicos_lote([ticker_yahoo], periodo).get(ticker_yahoo, [])


def _serie(ticker_yahoo: str, periodo: str, intervalo: str) -> list[tuple[str, float]]:
    """Série (data ISO no fuso da bolsa, fechamento) para gráficos (endpoint chart)."""
    from datetime import datetime, timedelta, timezone

    dados = _yahoo_json(f"{YAHOO_CHART}{urllib.parse.quote(ticker_yahoo)}?range={periodo}&interval={intervalo}")
    resultados = ((dados or {}).get("chart") or {}).get("result") or []
    if not resultados:
        return []
    r = resultados[0]
    fuso = timezone(timedelta(seconds=(r.get("meta") or {}).get("gmtoffset", 0)))
    tempos = r.get("timestamp") or []
    fechamentos = ((r.get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
    return [(datetime.fromtimestamp(t, fuso).isoformat(), float(v)) for t, v in zip(tempos, fechamentos) if v is not None]


def _moeda(ticker_yahoo: str) -> str:
    if ticker_yahoo.endswith(".SA") or ticker_yahoo in ("^BVSP", "BRL=X", "EURBRL=X"):
        return "BRL"
    return "USD"


def _get_json_bcb(url: str) -> list:
    req = urllib.request.Request(url, headers={"User-Agent": "news-analytics-platform", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resposta:
        return json.load(resposta)


def ultimo_valor_sgs(codigo: int, get_json) -> dict:
    """Último valor de uma série do SGS do Banco Central.

    Para algumas séries (ex.: 4389, CDI anualizado) o endpoint `ultimos/1`
    responde HTTP 304 sem corpo; nesse caso consultamos os últimos 120 dias
    por intervalo de datas e usamos o valor mais recente.
    """
    from datetime import date, timedelta

    base = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
    try:
        dados = get_json(f"{base}/ultimos/1?formato=json")
    except Exception:  # noqa: BLE001 - qualquer falha: tenta o intervalo de datas
        hoje = date.today()
        inicio = hoje - timedelta(days=120)
        dados = get_json(f"{base}?formato=json&dataInicial={inicio:%d/%m/%Y}&dataFinal={hoje:%d/%m/%Y}")
    if not dados:
        raise RuntimeError(f"série {codigo} sem dados")
    dado = dados[-1]
    return {"valor": float(dado["valor"]), "data": dado["data"]}


def _buscar_serie_bcb(codigo: int) -> dict:
    return ultimo_valor_sgs(codigo, _get_json_bcb)


# ---------------------------------------------------------------------------
# Funções de alto nível (usadas pelas ferramentas e pela UI)
# ---------------------------------------------------------------------------

def obter_cotacoes(tickers: list[str]) -> list[dict]:
    """Cotações de vários ativos com uma única consulta ao Yahoo (na ordem pedida)."""
    normalizados = [normalizar_ticker(t) for t in tickers]
    try:
        series = _historicos_lote(list(dict.fromkeys(normalizados)), "1y")
    except Exception as erro:  # noqa: BLE001
        return [{"ticker": t, "erro": f"cotação indisponível: {erro}"} for t in normalizados]
    cotacoes = []
    for t in normalizados:
        try:
            cotacoes.append({"ticker": t, "moeda": _moeda(t), **resumir_historico(series.get(t, [])), "fonte": "Yahoo Finance"})
        except ValueError as erro:
            cotacoes.append({"ticker": t, "erro": f"cotação indisponível: {erro}"})
    return cotacoes


def obter_cotacao(ticker: str) -> dict:
    return obter_cotacoes([ticker])[0]


# Período exibido -> (period, interval) do Yahoo Finance
PERIODOS_GRAFICO = {
    "1d": ("1d", "5m"),
    "5d": ("5d", "30m"),
    "1mo": ("1mo", "1d"),
    "6mo": ("6mo", "1d"),
    "1y": ("1y", "1d"),
}


def obter_historico(ticker: str, periodo: str = "1mo") -> dict:
    """Pontos para gráfico: {ticker, periodo, pontos: [{t, v}], variacao_pct}."""
    ticker_yahoo = normalizar_ticker(ticker)
    if periodo not in PERIODOS_GRAFICO:
        return {"ticker": ticker_yahoo, "erro": f"período inválido: {periodo}"}
    try:
        serie = _serie(ticker_yahoo, *PERIODOS_GRAFICO[periodo])
    except Exception as erro:  # noqa: BLE001
        return {"ticker": ticker_yahoo, "erro": f"histórico indisponível: {erro}"}
    if not serie:
        return {"ticker": ticker_yahoo, "erro": "histórico indisponível: sem dados"}
    pontos = [{"t": t, "v": round(v, 4)} for t, v in serie]
    return {
        "ticker": ticker_yahoo,
        "periodo": periodo,
        "moeda": _moeda(ticker_yahoo),
        "pontos": pontos,
        "variacao_pct": _variacao(pontos[-1]["v"], pontos[0]["v"]),
        "fonte": "Yahoo Finance",
    }


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
    for nome, cotacao in zip(PANORAMA, obter_cotacoes(list(PANORAMA.values()))):
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
