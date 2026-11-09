from types import SimpleNamespace

import pytest
from agno.run.base import RunStatus
from agno.workflow.types import StepInput

from agente import passos
from agente.comum import mensagem_erro_amigavel


class ExecutorFalso:
    name = "Agente Falso"

    def __init__(self, resultado):
        self.resultado = resultado
        self.mensagens = []

    def run(self, mensagem, stream=False):
        self.mensagens.append(mensagem)
        return self.resultado


def test_passo_agente_repassa_saida_anterior():
    agente = ExecutorFalso(SimpleNamespace(content="ok", status=RunStatus.completed))
    passo = passos.passo_agente("teste", agente)
    saida = passo.executor(StepInput(input="tema", previous_step_content="dossiê"))
    assert saida.content == "ok"
    assert agente.mensagens == ["dossiê"]


def test_passo_agente_primeiro_passo_recebe_o_tema():
    agente = ExecutorFalso(SimpleNamespace(content="ok", status=RunStatus.completed))
    passos.passo_agente("teste", agente).executor(StepInput(input="Selic"))
    assert agente.mensagens == ["Selic"]


def test_passo_agente_expoe_erro_real_do_groq():
    erro_groq = "Error code: 413 - Request too large for model ... (TPM): Limit 8000, Requested 9103"
    agente = ExecutorFalso(SimpleNamespace(content=erro_groq, status=RunStatus.error))
    passo = passos.passo_agente("apuracao", agente)
    with pytest.raises(passos.ErroDoAgente, match="limite de tokens por minuto"):
        passo.executor(StepInput(input="tema"))


def test_passo_agente_sem_conteudo():
    agente = ExecutorFalso(SimpleNamespace(content="", status=RunStatus.completed))
    with pytest.raises(passos.ErroDoAgente, match="não retornou conteúdo"):
        passos.passo_agente("x", agente).executor(StepInput(input="tema"))


def test_passo_agente_configura_retries():
    passo = passos.passo_agente("x", ExecutorFalso(None), max_retries=0)
    assert passo.name == "x"
    assert passo.max_retries == 0


def test_modelo_repete_chamada_de_ferramenta_invalida():
    from agno.exceptions import ModelProviderError

    from agente.comum import GroqTolerante, criar_modelo

    modelo = criar_modelo()
    assert isinstance(modelo, GroqTolerante)
    assert modelo.retries >= 1
    invalida = ModelProviderError(
        message="Tool call validation failed ... 'code': 'tool_use_failed'", status_code=400
    )
    outro_400 = ModelProviderError(message="bad request", status_code=400)
    assert modelo._is_retryable_error(invalida) is True
    assert modelo._is_retryable_error(outro_400) is False


def test_busca_instrui_argumento_query():
    from agente.comum import criar_busca

    busca = criar_busca()
    assert busca.add_instructions is True
    assert '"query"' in busca.instructions


@pytest.mark.parametrize(
    ("erro", "trecho"),
    [
        ("Error code: 413 - Request too large", "limite de tokens por minuto"),
        ("Error code: 429 - rate_limit_exceeded", "Aguarde"),
        (
            "429 rate_limit_exceeded on tokens per day (TPD): Limit 200000. Please try again in 10m58.8s.",
            "libera em 10m58.8s",
        ),
        ("Error code: 401 - invalid_api_key", "inválida"),
        ("outro erro", "outro erro"),
    ],
)
def test_mensagem_erro_amigavel(erro, trecho):
    assert trecho in mensagem_erro_amigavel(erro)
