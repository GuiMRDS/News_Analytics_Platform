"""Medidor de tokens do Groq (card da sidebar). Sem rede: httpx.MockTransport."""

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from agente import comum
from agente.uso_groq import TPD_PADRAO, MedidorGroq
from api import servidor

URL = "https://api.groq.com/openai/v1/chat/completions"
CABECALHOS = {
    "x-ratelimit-limit-tokens": "8000", "x-ratelimit-remaining-tokens": "6100",
    "x-ratelimit-limit-requests": "1000", "x-ratelimit-remaining-requests": "987",
}
ERRO_TPD = {"error": {"message": "Rate limit reached for model `openai/gpt-oss-20b` ... on tokens per day (TPD): "
                                 "Limit 200000, Used 198392, Requested 2232. Please try again in 4m29.5s.",
                      "type": "tokens", "code": "rate_limit_exceeded"}}


def transporte(request: httpx.Request) -> httpx.Response:
    modelo = json.loads(request.content)["model"]
    if modelo == "esgotado":
        return httpx.Response(429, json=ERRO_TPD)
    return httpx.Response(200, headers=CABECALHOS, json={"choices": [], "usage": {"total_tokens": 1500}})


def cliente(medidor):
    return httpx.Client(transport=httpx.MockTransport(transporte), event_hooks={"response": [medidor.hook_resposta]})


def test_hook_registra_limites_e_tokens(tmp_path):
    m = MedidorGroq(tmp_path / "uso.json")
    with cliente(m) as c:
        r = c.post(URL, json={"model": "openai/gpt-oss-20b", "messages": []})
        assert r.json()["usage"]["total_tokens"] == 1500  # o corpo continua legível para o SDK
        c.post(URL, json={"model": "openai/gpt-oss-20b", "messages": []})
    u = m.uso("openai/gpt-oss-20b")
    assert u["tokens_24h"] == 3000 and u["chamadas_24h"] == 2
    assert u["tpd_limite"] == TPD_PADRAO and u["tpd_restante"] == TPD_PADRAO - 3000
    assert (u["tpm_restante"], u["tpm_limite"], u["rpd_restante"], u["rpd_limite"]) == (6100, 8000, 987, 1000)


def test_429_traz_o_valor_oficial_do_groq(tmp_path):
    m = MedidorGroq(tmp_path / "uso.json")
    with cliente(m) as c:
        c.post(URL, json={"model": "esgotado", "messages": []})
    u = m.uso("esgotado")
    assert u["tokens_24h"] == 198392 and u["tpd_limite"] == 200000
    assert u["fonte_24h"].startswith("Groq")


def test_janela_de_24h_e_persistencia(tmp_path, monkeypatch):
    arquivo = tmp_path / "uso.json"
    m = MedidorGroq(arquivo)
    m.registrar("x", 200, {}, {"usage": {"total_tokens": 700}})
    m._salvar(forcar=True)
    assert MedidorGroq(arquivo).uso("x")["tokens_24h"] == 700  # sobrevive ao reinício
    agora = __import__("time").time()
    monkeypatch.setattr("agente.uso_groq.time.time", lambda: agora + 24 * 3600 + 1)
    assert m.uso("x")["tokens_24h"] == 0  # saiu da janela móvel


def test_hook_ignora_outras_urls_e_nunca_quebra(tmp_path):
    m = MedidorGroq(tmp_path / "uso.json")
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, text="não é json")),
                      event_hooks={"response": [m.hook_resposta]}) as c:
        assert c.post(URL, content=b"lixo").status_code == 200
        assert c.get("https://api.groq.com/openai/v1/models").status_code == 200
    assert m.uso("?")["tokens_24h"] == 0


def test_modelos_usam_o_cliente_com_medidor():
    assert comum.criar_modelo().http_client is comum.cliente_http_groq()


def test_status_e_sondagem_da_api(monkeypatch, tmp_path):
    medidor = MedidorGroq(tmp_path / "uso.json")
    monkeypatch.setattr(servidor, "medidor_groq", medidor)
    monkeypatch.setattr(servidor, "cliente_http_groq", lambda: cliente(medidor))
    monkeypatch.setenv("GROQ_MODELOS_RESERVA", "esgotado")
    api = TestClient(servidor.app)

    status = api.get("/api/status").json()
    assert [u["modelo"] for u in status["uso_groq"]] == ["openai/gpt-oss-20b", "esgotado"]

    r = api.post("/api/groq/sondar").json()
    assert [s["ok"] for s in r["sondagem"]] == [True, False]
    uso = {u["modelo"]: u for u in r["uso_groq"]}
    assert uso["openai/gpt-oss-20b"]["tpm_restante"] == 6100
    assert uso["esgotado"]["tokens_24h"] == 198392
    # a cota do modelo esgotado foi registrada (troca automática de modelo)
    assert {c["modelo"]: c["disponivel"] for c in comum.situacao_cota()}["esgotado"] is False


def test_sondagem_sem_chave(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert TestClient(servidor.app).post("/api/groq/sondar").status_code == 503


@pytest.fixture(autouse=True)
def _chave(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "chave-de-teste")
