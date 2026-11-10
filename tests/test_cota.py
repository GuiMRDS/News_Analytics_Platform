"""Cota diária do Groq: troca automática de modelo e falha rápida. Sem rede."""

import json

import pytest
from agno.exceptions import ModelProviderError
from agno.tools.websearch import WebSearchTools

from agente import comum

ERRO_TPD = (
    "Error code: 429 - Rate limit reached for model `openai/gpt-oss-20b` ... on tokens per day (TPD): "
    "Limit 200000, Used 198392, Requested 2232. Please try again in 4m29.567999999s."
)


def _erro(texto=ERRO_TPD, status=429):
    return ModelProviderError(message=texto, status_code=status)


@pytest.mark.parametrize(
    ("texto", "segundos"),
    [
        ("Please try again in 4m29.5s.", 269.5),
        ("Please try again in 1h2m3s.", 3723),
        ("Please try again in 45.2s.", 45.2),
        ("sem prazo", None),
    ],
)
def test_segundos_ate_liberar(texto, segundos):
    assert comum.segundos_ate_liberar(texto) == pytest.approx(segundos) if segundos else comum.segundos_ate_liberar(texto) is None


def test_modelos_configurados(monkeypatch):
    assert comum.modelos_configurados() == ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]
    monkeypatch.setenv("GROQ_MODEL_ID", "a")
    monkeypatch.setenv("GROQ_MODELOS_RESERVA", " b, a ,c ")
    assert comum.modelos_configurados() == ["a", "b", "c"]  # sem duplicatas, na ordem
    monkeypatch.setenv("GROQ_MODELOS_RESERVA", "")
    assert comum.modelos_configurados() == ["a"]


def test_registro_de_cota_e_modelo_disponivel():
    assert comum.modelo_disponivel() == "openai/gpt-oss-20b"
    comum.registrar_cota_esgotada("openai/gpt-oss-20b", 300)
    assert comum.modelo_disponivel() == "openai/gpt-oss-120b"
    situacao = {s["modelo"]: s for s in comum.situacao_cota()}
    assert situacao["openai/gpt-oss-20b"]["disponivel"] is False
    assert 290 <= situacao["openai/gpt-oss-20b"]["libera_em_s"] <= 300
    comum.registrar_cota_esgotada("openai/gpt-oss-120b", 60)
    assert comum.modelo_disponivel() is None
    assert "~1 min" in comum.resumo_cota_esgotada()


def test_cota_libera_depois_do_prazo(monkeypatch):
    comum.registrar_cota_esgotada("openai/gpt-oss-20b", 10)
    agora = comum.time.time()
    monkeypatch.setattr(comum.time, "time", lambda: agora + 11)
    assert comum.modelo_disponivel() == "openai/gpt-oss-20b"


def test_modelo_troca_para_reserva_quando_cota_diaria_acaba():
    modelo = comum.criar_modelo()
    assert modelo.id == "openai/gpt-oss-20b"
    assert modelo._is_retryable_error(_erro()) is True  # repete... com o modelo reserva
    assert modelo.id == "openai/gpt-oss-120b"
    # Outros agentes criados depois já começam na reserva
    assert comum.criar_modelo().id == "openai/gpt-oss-120b"


def test_modelo_falha_rapido_sem_reserva(monkeypatch):
    monkeypatch.setenv("GROQ_MODELOS_RESERVA", "")
    modelo = comum.criar_modelo()
    assert modelo._is_retryable_error(_erro()) is False  # não insiste
    with pytest.raises(comum.CotaEsgotada, match="esgotada em todos os modelos"):
        modelo._escolher_modelo()


def test_agente_criado_antes_tambem_troca_de_modelo():
    antigo = comum.criar_modelo()  # ex.: agente instanciado no import do workflow
    comum.registrar_cota_esgotada("openai/gpt-oss-20b", 300)
    antigo._escolher_modelo()
    assert antigo.id == "openai/gpt-oss-120b"


def test_outros_erros_mantem_o_comportamento():
    modelo = comum.criar_modelo()
    assert modelo._is_retryable_error(_erro("tool_use_failed: missing properties 'query'", 400)) is True
    assert modelo._is_retryable_error(_erro("bad request", 400)) is False
    assert modelo.id == "openai/gpt-oss-20b"  # não trocou de modelo


def test_mensagem_quando_todas_as_cotas_acabaram(monkeypatch):
    monkeypatch.setenv("GROQ_MODELOS_RESERVA", "")
    comum.registrar_cota_esgotada("openai/gpt-oss-20b", 240)
    msg = comum.mensagem_erro_amigavel(ERRO_TPD)
    assert "todos os modelos" in msg and "~4 min" in msg and "GROQ_MODELOS_RESERVA" in msg
    assert comum.mensagem_erro_amigavel(msg) == msg  # mensagem pronta não é reescrita


def test_busca_sem_resultados_nao_levanta(monkeypatch):
    def falha(self, query, max_results=5):
        raise RuntimeError("No results found.")

    monkeypatch.setattr(WebSearchTools, "search_news", falha)
    monkeypatch.setattr(WebSearchTools, "web_search", falha)
    busca = comum.criar_busca()
    for funcao in (busca.search_news, busca.web_search):
        resposta = json.loads(funcao("Petrobras dividendos"))
        assert resposta["resultados"] == []
        assert "Nenhum resultado para 'Petrobras dividendos'" in resposta["aviso"]
    assert set(busca.functions) == {"web_search", "search_news"}
