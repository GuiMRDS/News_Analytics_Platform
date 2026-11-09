"""Testes da interface Streamlit (sem chamar o LLM)."""

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
        return SimpleNamespace(content=f"Matéria sobre {tema} ({self.nome})")


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


def test_app_renderiza_com_versao_padrao(falsos):
    at = _app()
    assert not at.exception
    assert at.title[0].value == "📰 Curadoria de Notícias"
    assert at.session_state["versao"] == registry.VERSAO_PADRAO
    assert len(at.chat_input) == 1


def test_chat_usa_a_versao_selecionada(falsos):
    at = _app()

    at.chat_input[0].set_value("Eleições").run()
    assert falsos["V4"].temas == ["Eleições"]

    # Troca de versão no meio da conversa
    at.session_state["versao"] = "V2"
    at.run()
    at.chat_input[0].set_value("Clima").run()
    assert falsos["V2"].temas == ["Clima"]

    mensagens = at.session_state["mensagens"]
    assert [m["papel"] for m in mensagens] == ["user", "assistant", "user", "assistant"]
    assert mensagens[1]["versao"] == registry.VERSOES["V4"].rotulo
    assert mensagens[3]["versao"] == registry.VERSOES["V2"].rotulo
    assert "Matéria sobre Clima (V2)" in mensagens[3]["conteudo"]


def test_chat_mostra_erro_do_workflow(monkeypatch):
    class Quebrado:
        def run(self, tema):
            raise RuntimeError("falha simulada")

    monkeypatch.setattr(registry, "carregar_workflow", lambda chave: Quebrado())
    at = _app()
    at.chat_input[0].set_value("Tema").run()
    assert not at.exception
    assert "falha simulada" in at.session_state["mensagens"][-1]["conteudo"]


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
