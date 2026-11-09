"""Testes da interface Streamlit (sem LLM e com dados de mercado simulados)."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

import registry

APP = str(Path(__file__).resolve().parent.parent / "ui" / "app.py")


class WorkflowFalso:
    def __init__(self, nome):
        self.nome = nome
        self.temas = []

    def run(self, tema):
        self.temas.append(tema)
        return SimpleNamespace(content=f"Matéria sobre {tema} ({self.nome})", status="COMPLETED")


@pytest.fixture
def falsos(monkeypatch):
    workflows = {chave: WorkflowFalso(chave) for chave in registry.VERSOES}
    monkeypatch.setattr(registry, "carregar_workflow", lambda chave: workflows[chave])
    return workflows


def _app():
    return AppTest.from_file(APP, default_timeout=60).run()


@pytest.mark.parametrize("chave", list(registry.VERSOES))
def test_registry_carrega_todas_as_versoes(chave):
    workflow = registry.carregar_workflow(chave)
    assert callable(getattr(workflow, "run", None))
    assert callable(getattr(workflow, "print_response", None))


def test_versao_padrao_e_a_do_investidor():
    assert registry.VERSAO_PADRAO == "V5"
    assert list(registry.VERSOES)[0] == "V5"


def test_app_renderiza_com_versao_padrao(falsos):
    at = _app()
    assert not at.exception
    assert at.title[0].value == "📈 Notícias para Investidores"
    assert at.session_state["versao"] == registry.VERSAO_PADRAO
    assert len(at.chat_input) == 1


def test_painel_de_mercado_na_sidebar(falsos):
    at = _app()
    metricas = {m.label: m.value for m in at.sidebar.metric}
    assert "Ibovespa" in metricas and "Dólar (R$)" in metricas
    texto = " ".join(md.value for md in at.sidebar.markdown)
    assert "Selic" in texto and "13,75" in texto
    assert "IPCA 12m" in texto and "4,58" in texto


def test_chat_usa_a_versao_selecionada(falsos):
    at = _app()

    at.chat_input[0].set_value("Selic").run()
    assert falsos["V5"].temas == ["Selic"]

    # Troca de versão no meio da conversa
    at.session_state["versao"] = "V2"
    at.run()
    at.chat_input[0].set_value("Clima").run()
    assert falsos["V2"].temas == ["Clima"]

    mensagens = at.session_state["mensagens"]
    assert [m["papel"] for m in mensagens] == ["user", "assistant", "user", "assistant"]
    assert mensagens[1]["versao"] == registry.VERSOES["V5"].rotulo
    assert mensagens[3]["versao"] == registry.VERSOES["V2"].rotulo
    assert "Matéria sobre Clima (V2)" in mensagens[3]["conteudo"]


def test_sugestao_dispara_pergunta(falsos):
    at = _app()
    at.button(key="sugestao_1").click().run()
    assert falsos["V5"].temas == ["Por que a Petrobras (PETR4) oscilou hoje?"]
    assert at.session_state["mensagens"][0]["conteudo"].startswith("Por que a Petrobras")


def test_chat_mostra_excecao_do_workflow(monkeypatch):
    class Quebrado:
        def run(self, tema):
            raise RuntimeError("Error code: 413 - Request too large")

    monkeypatch.setattr(registry, "carregar_workflow", lambda chave: Quebrado())
    at = _app()
    at.chat_input[0].set_value("Tema").run()
    assert not at.exception
    resposta = at.session_state["mensagens"][-1]["conteudo"]
    assert resposta.startswith("❌") and "limite de tokens por minuto" in resposta


def test_chat_mostra_status_de_erro_do_workflow(monkeypatch):
    class ComErro:
        def run(self, tema):
            return SimpleNamespace(content="Error code: 429 - rate_limit_exceeded", status="RunStatus.error")

    monkeypatch.setattr(registry, "carregar_workflow", lambda chave: ComErro())
    at = _app()
    at.chat_input[0].set_value("Tema").run()
    assert "Aguarde" in at.session_state["mensagens"][-1]["conteudo"]


def test_nova_conversa_limpa_historico(falsos):
    at = _app()
    at.chat_input[0].set_value("Tema").run()
    assert at.session_state["mensagens"]
    at.sidebar.button(key="nova_conversa").click().run()
    assert at.session_state["mensagens"] == []


def test_app_sem_api_key_mostra_erro(monkeypatch, falsos):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    at = _app()
    assert any("GROQ_API_KEY" in e.value for e in at.error)
    assert len(at.chat_input) == 0
