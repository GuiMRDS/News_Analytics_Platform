"""Testes da API (FastAPI) e do front-end servido. Sem LLM e sem rede."""

import json
import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api import registry, servidor
from api.execucao import Tarefa, etapas_do_executor, executar


# ---------------------------------------------------------------------------
# Eventos falsos com os mesmos nomes de classe do Agno
# ---------------------------------------------------------------------------

def _evento(nome, **campos):
    return type(nome, (), {})() if not campos else type(nome, (SimpleNamespace,), {})(**campos)


class WorkflowFalso:
    """Imita um Workflow do Agno: tem .steps e .run(stream=True) gera eventos."""

    def __init__(self, conteudo="# Matéria\n\nTexto [1].", falhar=None):
        self.steps = [SimpleNamespace(name="pesquisa"), SimpleNamespace(name="apuracao_loop"), SimpleNamespace(name="redacao")]
        self.conteudo, self.falhar, self.temas = conteudo, falhar, []

    def run(self, tema, stream=False, stream_events=False):
        self.temas.append(tema)
        yield _evento("WorkflowStartedEvent", step_name=None)
        yield _evento("StepStartedEvent", step_name="pesquisa")
        yield _evento("StepCompletedEvent", step_name="pesquisa")
        yield _evento("LoopExecutionStartedEvent", step_name="apuracao_loop")
        yield _evento("LoopIterationStartedEvent", step_name="apuracao_loop", iteration=1, max_iterations=2)
        yield _evento("StepStartedEvent", step_name="apuracao")  # passo interno do loop: ignorado
        yield _evento("LoopExecutionCompletedEvent", step_name="apuracao_loop")
        if self.falhar:
            yield _evento("StepErrorEvent", step_name="redacao")
            yield _evento("WorkflowErrorEvent", step_name=None, error=self.falhar)
            return
        yield _evento("StepStartedEvent", step_name="redacao")
        yield _evento("StepCompletedEvent", step_name="redacao")
        yield _evento("WorkflowCompletedEvent", step_name=None, content=self.conteudo)


class AgenteFalso:
    """Imita um Agent (V1): sem .steps, .run(stream=False) devolve o resultado."""

    def __init__(self, conteudo="Matéria do agente", status="COMPLETED"):
        self.conteudo, self.status = conteudo, status

    def run(self, tema, stream=False):
        return SimpleNamespace(content=self.conteudo, status=self.status)


@pytest.fixture
def cliente(monkeypatch, tmp_path):
    servidor.cache.limpar()
    monkeypatch.setattr(servidor, "OUTPUT_DIR", tmp_path)
    return TestClient(servidor.app)


def _aguardar(cliente, tarefa_id, limite=5.0):
    fim = time.time() + limite
    while time.time() < fim:
        estado = cliente.get(f"/api/perguntas/{tarefa_id}").json()
        if estado["concluida"]:
            return estado
        time.sleep(0.02)
    raise AssertionError("a tarefa não terminou a tempo")


# ---------------------------------------------------------------------------
# Front-end e sistema
# ---------------------------------------------------------------------------

def test_front_end_servido(cliente):
    r = cliente.get("/")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    assert "Quantum Terminal" in r.text and "/static/js/app.js" in r.text
    assert cliente.get("/static/css/quantum.css").status_code == 200
    js = cliente.get("/static/js/app.js")
    assert js.status_code == 200 and "/api/perguntas" in js.text


def test_status(cliente):
    s = cliente.get("/api/status").json()
    assert s["api_key_configurada"] is True  # chave fictícia do conftest
    assert s["versao_padrao"] == "V5"
    assert s["busca_backend"] == "auto"


def test_versoes(cliente):
    dados = cliente.get("/api/versoes").json()
    assert dados["padrao"] == registry.VERSAO_PADRAO == "V5"
    assert [v["chave"] for v in dados["versoes"]] == ["V5", "V4", "V3", "V2", "V1"]
    assert "modulo" not in dados["versoes"][0]  # detalhes internos não vazam


@pytest.mark.parametrize("chave", list(registry.VERSOES))
def test_registry_carrega_todas_as_versoes(chave):
    executor = registry.carregar_workflow(chave)
    assert callable(getattr(executor, "run", None))
    assert etapas_do_executor(executor)


def test_etapas_da_v5_tem_rotulos():
    etapas = etapas_do_executor(registry.carregar_workflow("V5"))
    assert [e["id"] for e in etapas][:2] == ["pesquisa", "apuracao_loop"]
    assert all(e["rotulo"] != e["id"] for e in etapas)  # todas as etapas têm rótulo amigável


# ---------------------------------------------------------------------------
# Mercado
# ---------------------------------------------------------------------------

def test_painel_de_mercado(cliente):
    dados = cliente.get("/api/mercado").json()
    assert dados["panorama"]["Ibovespa"]["preco"] == 125.1
    assert dados["indicadores"]["selic_meta_aa"]["valor"] == 13.75


def test_painel_usa_cache(cliente, monkeypatch):
    chamadas = []
    original = servidor.mercado.obter_indicadores
    monkeypatch.setattr(servidor.mercado, "obter_indicadores", lambda: chamadas.append(1) or original())
    cliente.get("/api/mercado")
    cliente.get("/api/mercado")
    assert len(chamadas) == 1


def test_cache_nao_guarda_resposta_parcial(cliente, monkeypatch):
    """Ex.: o BCB falha só no CDI (HTTP 304) — a próxima chamada deve tentar de novo."""
    chamadas = []

    def parcial(codigo):
        chamadas.append(codigo)
        if codigo == 4389:
            raise OSError("HTTP Error 304: Not Modified")
        return {"valor": 1.0, "data": "01/01/2026"}

    monkeypatch.setattr(servidor.mercado, "_buscar_serie_bcb", parcial)
    primeira = cliente.get("/api/mercado").json()
    assert "erro" in primeira["indicadores"]["cdi_aa"]
    cliente.get("/api/mercado")
    assert chamadas.count(4389) == 2  # não ficou em cache


def test_cotacoes(cliente):
    dados = cliente.get("/api/mercado/cotacoes?tickers=petr4, VALE3").json()["cotacoes"]
    assert [c["entrada"] for c in dados] == ["PETR4", "VALE3"]
    assert dados[0]["ticker"] == "PETR4.SA" and dados[0]["preco"] == 125.1


def test_cotacoes_validacao(cliente):
    assert cliente.get("/api/mercado/cotacoes?tickers=,").status_code == 400
    muitos = ",".join(f"T{i}" for i in range(21))
    assert cliente.get(f"/api/mercado/cotacoes?tickers={muitos}").status_code == 400


def test_historico(cliente):
    h = cliente.get("/api/mercado/historico/IBOV?periodo=1mo").json()
    assert h["ticker"] == "^BVSP" and len(h["pontos"]) == 20
    assert h["pontos"][0] == {"t": "2026-10-01T00:00:00-03:00", "v": 101}
    assert h["variacao_pct"] == round((120 / 101 - 1) * 100, 2)
    assert cliente.get("/api/mercado/historico/IBOV?periodo=10y").status_code == 400
    assert "erro" in cliente.get("/api/mercado/historico/INEXISTENTE").json()


def test_simulacao(cliente):
    r = cliente.post("/api/simulacao/renda-fixa", json={"valor": 10000, "taxa_anual_pct": 12, "meses": 12})
    assert r.status_code == 200 and r.json()["valor_liquido"] == 10960.0
    invalida = cliente.post("/api/simulacao/renda-fixa", json={"valor": -1, "taxa_anual_pct": 12, "meses": 12})
    assert invalida.status_code == 422


# ---------------------------------------------------------------------------
# Matérias
# ---------------------------------------------------------------------------

def test_materias_lista_e_le(cliente, tmp_path):
    (tmp_path / "V5").mkdir()
    (tmp_path / "V5" / "materia_selic_2026-11-09.md").write_text("# Selic mantida em 13,75%\n\nCorpo.", encoding="utf-8")
    (tmp_path / "V5" / "ignorar.txt").write_text("x", encoding="utf-8")
    lista = cliente.get("/api/materias").json()["materias"]
    assert len(lista) == 1 and lista[0]["titulo"] == "Selic mantida em 13,75%" and lista[0]["versao"] == "V5"
    m = cliente.get("/api/materias/V5/materia_selic_2026-11-09.md").json()
    assert m["markdown"].startswith("# Selic")


def test_materias_bloqueia_caminhos_invalidos(cliente):
    assert cliente.get("/api/materias/V5/..%2F..%2Fpyproject.toml").status_code in (400, 404)
    assert cliente.get("/api/materias/etc/passwd.md").status_code == 400
    assert cliente.get("/api/materias/V5/nao_existe.md").status_code == 404


def test_materias_sem_pasta_output(cliente, monkeypatch, tmp_path):
    monkeypatch.setattr(servidor, "OUTPUT_DIR", tmp_path / "nao_existe")
    assert cliente.get("/api/materias").json() == {"materias": []}


# ---------------------------------------------------------------------------
# Perguntas
# ---------------------------------------------------------------------------

def test_pergunta_com_workflow_emite_eventos(cliente, monkeypatch):
    falso = WorkflowFalso()
    monkeypatch.setattr(registry, "carregar_workflow", lambda chave: falso)
    r = cliente.post("/api/perguntas", json={"tema": "Copom e renda fixa", "versao": "V5"})
    assert r.status_code == 202
    assert [e["id"] for e in r.json()["etapas"]] == ["pesquisa", "apuracao_loop", "redacao"]

    estado = _aguardar(cliente, r.json()["id"])
    assert falso.temas == ["Copom e renda fixa"]
    assert estado["conteudo"].startswith("# Matéria") and estado["erro"] is None
    tipos = [(e["tipo"], e.get("id"), e.get("status")) for e in estado["eventos"]]
    assert tipos[0][0] == "inicio" and tipos[-1][0] == "fim"
    assert ("etapa", "pesquisa", "iniciada") in tipos and ("etapa", "redacao", "concluida") in tipos
    assert ("etapa", "apuracao", "iniciada") not in tipos  # passo interno do loop não aparece
    assert any(e["tipo"] == "tentativa" and e["atual"] == 1 and e["maximo"] == 2 for e in estado["eventos"])


def test_pergunta_sse_transmite_ate_o_fim(cliente, monkeypatch):
    monkeypatch.setattr(registry, "carregar_workflow", lambda chave: WorkflowFalso())
    tarefa_id = cliente.post("/api/perguntas", json={"tema": "Dólar hoje", "versao": "V4"}).json()["id"]
    with cliente.stream("GET", f"/api/perguntas/{tarefa_id}/eventos") as r:
        assert r.headers["content-type"].startswith("text/event-stream")
        eventos = [json.loads(linha[6:]) for linha in r.iter_lines() if linha.startswith("data: ")]
    assert eventos[0]["tipo"] == "inicio" and eventos[-1]["tipo"] == "fim"
    assert any(e["tipo"] == "conteudo" for e in eventos)


def test_pergunta_com_erro_do_workflow(cliente, monkeypatch):
    monkeypatch.setattr(registry, "carregar_workflow", lambda chave: WorkflowFalso(falhar="Error code: 413 - Request too large"))
    estado = _aguardar(cliente, cliente.post("/api/perguntas", json={"tema": "Tema", "versao": "V5"}).json()["id"])
    assert estado["conteudo"] is None
    assert "limite de tokens por minuto" in estado["erro"]
    assert any(e.get("id") == "redacao" and e.get("status") == "erro" for e in estado["eventos"])


def test_pergunta_com_agente_unico(cliente, monkeypatch):
    monkeypatch.setattr(registry, "carregar_workflow", lambda chave: AgenteFalso())
    r = cliente.post("/api/perguntas", json={"tema": "Tema do agente", "versao": "V1"})
    assert r.json()["etapas"] == [{"id": "agente", "rotulo": "Agente único"}]
    estado = _aguardar(cliente, r.json()["id"])
    assert estado["conteudo"] == "Matéria do agente"


def test_pergunta_agente_com_status_de_erro(cliente, monkeypatch):
    monkeypatch.setattr(registry, "carregar_workflow", lambda chave: AgenteFalso("Error code: 429 - rate_limit_exceeded", "RunStatus.error"))
    estado = _aguardar(cliente, cliente.post("/api/perguntas", json={"tema": "Tema", "versao": "V1"}).json()["id"])
    assert "Aguarde" in estado["erro"]


def test_pergunta_validacoes(cliente, monkeypatch):
    assert cliente.post("/api/perguntas", json={"tema": "Tema", "versao": "V9"}).status_code == 400
    assert cliente.post("/api/perguntas", json={"tema": "ab"}).status_code == 422
    assert cliente.get("/api/perguntas/naoexiste").status_code == 404
    assert cliente.get("/api/perguntas/naoexiste/eventos").status_code == 404
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    r = cliente.post("/api/perguntas", json={"tema": "Tema válido"})
    assert r.status_code == 503 and "GROQ_API_KEY" in r.json()["detail"]


def test_executar_sem_conteudo_vira_erro():
    class Vazio(WorkflowFalso):
        def run(self, tema, stream=False, stream_events=False):
            yield _evento("WorkflowCompletedEvent", step_name=None, content="")

    tarefa = Tarefa(tema="x", versao="V5")
    executar(tarefa, Vazio())
    assert tarefa.concluida and "sem conteúdo" in tarefa.resumo()["erro"]
