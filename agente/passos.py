"""Passos reutilizáveis de workflow (executores determinísticos e wrappers)."""

import re
import unicodedata
import uuid
from contextvars import ContextVar
from datetime import date
from pathlib import Path
from typing import Any, Callable, List, Protocol

from agno.run.base import RunStatus
from agno.workflow import Step
from agno.workflow.types import StepInput, StepOutput

from agente.comum import BASE_DIR, contar_fontes, mensagem_erro_amigavel


class ErroDoAgente(RuntimeError):
    """Falha de um agente/equipe dentro do workflow, com a causa real."""


class ExecucaoCancelada(RuntimeError):
    """A execução foi cancelada pelo usuário."""


class ControleDeExecucao(Protocol):
    """O que quem dispara o workflow (ex.: api.execucao.Tarefa) expõe para o cancelamento."""

    cancelada: bool

    def registrar_run(self, run_id: str) -> None: ...


# Controle da execução corrente (definido por quem roda o workflow, na mesma thread)
CONTROLE_EXECUCAO: ContextVar[ControleDeExecucao | None] = ContextVar("controle_execucao", default=None)


def verificar_cancelamento() -> None:
    controle = CONTROLE_EXECUCAO.get()
    if controle is not None and controle.cancelada:
        raise ExecucaoCancelada("execução cancelada pelo usuário")


def novo_run_id() -> str:
    """run_id do Agno registrado no controle corrente, para poder ser cancelado."""
    run_id = uuid.uuid4().hex
    controle = CONTROLE_EXECUCAO.get()
    if controle is not None:
        controle.registrar_run(run_id)
    return run_id


def _mensagem_do_passo(step_input: StepInput) -> str:
    """Mesma regra do Agno: o passo recebe a saída anterior ou, no primeiro passo, o tema."""
    anterior = step_input.previous_step_content
    if anterior:
        return str(anterior)
    return step_input.get_input_as_string() or ""


def passo_agente(nome: str, executor: Any, descricao: str = "", max_retries: int = 1) -> Step:
    """Cria um Step que roda um Agent/Team e falha com a causa real.

    No Agno 2.4.8, quando um agente falha dentro de um Step (ex.: limite de tokens
    do Groq), o erro original é escondido por
    "'NoneType' object has no attribute 'parent_run_id'". Este wrapper roda o
    executor sem streaming, verifica o status e levanta ErroDoAgente com uma
    mensagem compreensível.
    """

    def executar(step_input: StepInput) -> StepOutput:
        verificar_cancelamento()
        # run_id registrado: cancelar a tarefa interrompe o agente entre as chamadas ao modelo
        resultado = executor.run(_mensagem_do_passo(step_input), stream=False, run_id=novo_run_id())
        verificar_cancelamento()
        conteudo = getattr(resultado, "content", None)
        if resultado is None or getattr(resultado, "status", None) == RunStatus.error:
            raise ErroDoAgente(
                f"Falha em '{nome}' ({getattr(executor, 'name', '?')}): "
                f"{mensagem_erro_amigavel(conteudo or 'sem resposta')}"
            )
        if not conteudo:
            raise ErroDoAgente(f"'{nome}' ({getattr(executor, 'name', '?')}) não retornou conteúdo.")
        return StepOutput(content=str(conteudo))

    executar.__name__ = f"executar_{nome}"
    return Step(name=nome, description=descricao, executor=executar, max_retries=max_retries)


def criar_condicao_fontes(min_fontes: int) -> Callable[[List[StepOutput]], bool]:
    """Condição de parada do loop de apuração: a última iteração atingiu o mínimo?"""

    def fontes_suficientes(outputs: List[StepOutput]) -> bool:
        if not outputs:
            return False
        return contar_fontes(str(outputs[-1].content or "")) >= min_fontes

    return fontes_suficientes


def validar_fontes(step_input: StepInput, min_fontes: int, max_tentativas: int) -> StepOutput:
    """Valida (sem LLM) a quantidade de fontes do dossiê e anota o resultado."""
    dossie = str(step_input.previous_step_content or "")
    total = contar_fontes(dossie)

    if total >= min_fontes:
        status = f"✅ APROVADO — {total} fontes distintas (mínimo {min_fontes})."
    else:
        status = (
            f"⚠️ INSUFICIENTE — apenas {total} fontes distintas (mínimo {min_fontes}) "
            f"após {max_tentativas} tentativas de apuração. "
            "O redator deve incluir a nota de fontes limitadas."
        )

    return StepOutput(content=f"## VALIDAÇÃO DE FONTES\n\n{status}\n\n{dossie}")


def slug(texto: str, limite: int = 50) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^a-zA-Z0-9]+", "_", texto).strip("_").lower()
    return texto[:limite].rstrip("_") or "materia"


def exportar_markdown(step_input: StepInput, pasta: Path) -> StepOutput:
    """Salva a matéria final em <pasta>/materia_<tema>_<data>.md."""
    verificar_cancelamento()  # pesquisa cancelada não gera arquivo
    materia = str(step_input.previous_step_content or "").strip()
    tema = step_input.get_input_as_string() or "materia"

    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / f"materia_{slug(tema)}_{date.today().isoformat()}.md"
    arquivo.write_text(materia + "\n", encoding="utf-8")

    try:
        caminho = arquivo.relative_to(BASE_DIR).as_posix()
    except ValueError:
        caminho = arquivo.as_posix()
    return StepOutput(content=f"{materia}\n\n---\n_Matéria salva em `{caminho}`_")
