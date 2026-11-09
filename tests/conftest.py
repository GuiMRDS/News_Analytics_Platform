"""Configuração global dos testes.

Nenhum teste chama o LLM, faz buscas na web ou consulta dados de mercado:
os agentes são apenas instanciados (o que não exige rede), a UI usa
workflows falsos e as fontes de mercado (Yahoo Finance/BCB) são simuladas.
"""

import os

import pytest

# Chave fictícia: permite importar os módulos sem .env. Definida antes de
# qualquer import de `agente`, pois `comum` chama load_dotenv no import
# (load_dotenv não sobrescreve variáveis já definidas).
os.environ.setdefault("GROQ_API_KEY", "chave-de-teste")

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
    from agente import ferramentas_mercado as fm

    def historico(ticker, periodo="1y"):
        if ticker == "INEXISTENTE":
            return []
        return list(HISTORICO_FALSO)

    monkeypatch.setattr(fm, "_historico", historico)
    monkeypatch.setattr(fm, "_buscar_serie_bcb", lambda codigo: dict(SERIES_FALSAS[codigo]))
