"""Configuração global dos testes.

Nenhum teste chama o LLM, faz buscas na web ou consulta dados de mercado:
os agentes são apenas instanciados (o que não exige rede), a API usa
workflows falsos e as fontes de mercado (Yahoo Finance/BCB) são simuladas.
"""

import os

import pytest

# Chave fictícia: permite importar os módulos sem .env. Definida antes de
# qualquer import de `agente`, pois `comum` chama load_dotenv no import
# (load_dotenv não sobrescreve variáveis já definidas).
os.environ.setdefault("GROQ_API_KEY", "chave-de-teste")

from agente import ferramentas_mercado as fm  # noqa: E402

# Funções reais de acesso a dados, guardadas antes de o fixture simulá-las
# (para os testes de parsing, que trocam só a camada HTTP).
REAIS = {nome: getattr(fm, nome) for nome in ("_historicos_lote", "_serie", "_buscar_serie_bcb")}

# 252 pregões fictícios: de 100 até 125,1 (alta constante de 0,1 por dia)
HISTORICO_FALSO = [100 + i * 0.1 for i in range(252)]

SERIES_FALSAS = {
    432: {"valor": 13.75, "data": "05/11/2026"},
    4389: {"valor": 13.65, "data": "06/11/2026"},
    13522: {"valor": 4.58, "data": "01/09/2026"},
    1: {"valor": 5.5013, "data": "06/11/2026"},
}


@pytest.fixture(autouse=True)
def mercado_simulado(monkeypatch):
    def lote(tickers, periodo="1y"):
        return {t: [] if t == "INEXISTENTE" else list(HISTORICO_FALSO) for t in tickers}

    def serie(ticker, periodo, intervalo):
        if ticker == "INEXISTENTE":
            return []
        return [(f"2026-10-{d:02d}T00:00:00-03:00", 100 + d) for d in range(1, 21)]

    monkeypatch.setattr(fm, "_historicos_lote", lote)
    monkeypatch.setattr(fm, "_serie", serie)
    monkeypatch.setattr(fm, "_buscar_serie_bcb", lambda codigo: dict(SERIES_FALSAS[codigo]))


@pytest.fixture
def funcoes_reais():
    """Acesso às implementações reais (use junto com um _yahoo_json simulado)."""
    return REAIS
