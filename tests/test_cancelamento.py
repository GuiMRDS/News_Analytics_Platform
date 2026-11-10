"""Cancelamento de perguntas: passos, tarefa e API. Sem LLM e sem rede."""

import threading
import time
from types import SimpleNamespace

import pytest
from agno.run.base import RunStatus
from agno.run.cancel import is_cancelled, register_run
from agno.workflow.types import StepInput
from fastapi.testclient import TestClient

from agente import passos
from api import registry, servidor
from api.execucao import Tarefa


class Controle:
    def __init__(self, cancelada=False):
        self.cancelada, self.run_ids = cancelada, []

    def registrar_run(self, run_id):
        self.run_ids.append(run_id)


class AgenteFalso:
    name = "Agente"

    def __init__(self):
        self.run_ids = []

    def run(self, mensagem, stream=False, run_id=None):
        self.run_ids.append(run_id)
        return SimpleNamespace(content="ok", status=RunStatus.completed)


@pytest.fixture
def controle():
    def ativar(c):
        token = passos.CONTROLE_EXECUCAO.set(c)
        tokens.append(token)
        return c

    tokens = []
    yield ativar
    for t in reversed(tokens):
        passos.CONTROLE_EXECUCAO.reset(t)


# ---------------------------------------------------------------------------
# Passos
# ---------------------------------------------------------------------------

def test_passo_registra_e_repassa_run_id(controle):
    c = controle(Controle())
    agente = AgenteFalso()
    passos.passo_agente("x", agente).executor(StepInput(input="tema"))
    assert agente.run_ids and agente.run_ids == c.run_ids  # o mesmo run_id foi registrado e usado


def test_passo_nao_roda_se_cancelado(controle):
    controle(Controle(cancelada=True))
    agente = AgenteFalso()
    with pytest.raises(passos.ExecucaoCancelada):
        passos.passo_agente("x", agente).executor(StepInput(input="tema"))
    assert agente.run_ids == []  # o agente nem foi chamado


def test_passo_cancelado_durante_a_execucao(controle):
    c = controle(Controle())

    class Interrompido(AgenteFalso):
        def run(self, mensagem, stream=False, run_id=None):
            c.cancelada = True  # o usuário cancelou enquanto o agente trabalhava
            return SimpleNamespace(content="parcial", status=RunStatus.cancelled)

    with pytest.raises(passos.ExecucaoCancelada):
        passos.passo_agente("x", Interrompido()).executor(StepInput(input="tema"))


def test_exportacao_nao_salva_se_cancelado(controle, tmp_path):
    controle(Controle(cancelada=True))
    with pytest.raises(passos.ExecucaoCancelada):
        passos.exportar_markdown(StepInput(input="tema", previous_step_content="# Matéria"), tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_sem_controle_funciona_como_antes():
    agente = AgenteFalso()  # ex.: rodando no terminal com python -m agente.agente_curador_v5
    assert passos.passo_agente("x", agente).executor(StepInput(input="tema")).content == "ok"
    assert agente.run_ids[0]  # ainda recebe um run_id


# ---------------------------------------------------------------------------
# Tarefa
# ---------------------------------------------------------------------------

def _ate(condicao, limite=2.0):
    fim = time.time() + limite
    while time.time() < fim:
        if condicao():
            return True
        time.sleep(0.02)
    return False


def test_tarefa_cancelar_interrompe_runs_do_agno():
    t = Tarefa(tema="x", versao="V5")
    t.registrar_run("run-ativo-1")
    register_run("run-ativo-1")  # o agente já começou (o Agno registrou o run)
    assert t.cancelar() is True
    assert is_cancelled("run-ativo-1")
    assert t.eventos[-1]["tipo"] == "cancelado"
    assert t.cancelar() is False  # idempotente


def test_cancelamento_antes_de_o_agente_registrar_o_run():
    """Janela de corrida: o run_id foi criado, mas o agente ainda não chamou register_run."""
    t = Tarefa(tema="x", versao="V5")
    t.registrar_run("run-ainda-nao-iniciado")
    t.cancelar()
    register_run("run-ainda-nao-iniciado")  # o agente começa logo depois...
    assert _ate(lambda: is_cancelled("run-ainda-nao-iniciado"))  # ...e é cancelado mesmo assim

    t.registrar_run("run-tardio")  # passo que começou depois do cancelamento
    register_run("run-tardio")
    assert _ate(lambda: is_cancelled("run-tardio"))


def test_tarefa_concluida_nao_cancela():
    t = Tarefa(tema="x", versao="V5")
    t.concluida = True
    assert t.cancelar() is False


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

class WorkflowLento:
    """Workflow falso: cada etapa espera um sinal para terminar."""

    def __init__(self):
        self.steps = [SimpleNamespace(name=n) for n in ("pesquisa", "redacao", "exportacao")]
        self.liberar = threading.Event()
        self.executadas = []

    def run(self, tema, stream=False, stream_events=False):
        for nome in ("pesquisa", "redacao", "exportacao"):
            self.executadas.append(nome)
            yield type("StepStartedEvent", (SimpleNamespace,), {})(step_name=nome)
            self.liberar.wait(2)
            yield type("StepCompletedEvent", (SimpleNamespace,), {})(step_name=nome)
        yield type("WorkflowCompletedEvent", (SimpleNamespace,), {})(step_name=None, content="# Matéria")


def _aguardar(cliente, tarefa_id, condicao, limite=5.0):
    fim = time.time() + limite
    while time.time() < fim:
        estado = cliente.get(f"/api/perguntas/{tarefa_id}").json()
        if condicao(estado):
            return estado
        time.sleep(0.02)
    raise AssertionError("condição não atingida a tempo")


def test_api_cancela_pesquisa_em_andamento(monkeypatch):
    workflow = WorkflowLento()
    monkeypatch.setattr(registry, "carregar_workflow", lambda chave: workflow)
    cliente = TestClient(servidor.app)
    tarefa_id = cliente.post("/api/perguntas", json={"tema": "Selic hoje"}).json()["id"]
    _aguardar(cliente, tarefa_id, lambda e: any(ev.get("status") == "iniciada" for ev in e["eventos"]))

    r = cliente.post(f"/api/perguntas/{tarefa_id}/cancelar")
    assert r.status_code == 200 and r.json()["cancelada"] is True
    workflow.liberar.set()  # a etapa em andamento termina...
    estado = _aguardar(cliente, tarefa_id, lambda e: e["concluida"])

    assert estado["cancelada"] is True
    assert estado["conteudo"] is None and estado["erro"] is None  # sem matéria e sem "erro"
    tipos = [e["tipo"] for e in estado["eventos"]]
    assert "cancelado" in tipos and tipos[-1] == "fim" and estado["eventos"][-1]["cancelada"] is True
    assert "exportacao" not in workflow.executadas  # ...mas o workflow não avança (nada é salvo)

    assert cliente.post(f"/api/perguntas/{tarefa_id}/cancelar").status_code == 409


def test_api_cancelar_inexistente_e_concluida(monkeypatch):
    cliente = TestClient(servidor.app)
    assert cliente.post("/api/perguntas/naoexiste/cancelar").status_code == 404

    workflow = WorkflowLento()
    workflow.liberar.set()
    monkeypatch.setattr(registry, "carregar_workflow", lambda chave: workflow)
    tarefa_id = cliente.post("/api/perguntas", json={"tema": "Selic hoje"}).json()["id"]
    _aguardar(cliente, tarefa_id, lambda e: e["concluida"])
    assert cliente.post(f"/api/perguntas/{tarefa_id}/cancelar").status_code == 409


def test_front_tem_botao_de_cancelar():
    js = TestClient(servidor.app).get("/static/js/app.js").text
    assert "/cancelar" in js and "AbortController" in js and "data-cancel" in js
