"""Execução das perguntas em segundo plano, com eventos de progresso.

Cada pergunta vira uma Tarefa que roda o agente/workflow numa thread. Os
eventos do Agno são traduzidos para eventos simples que o front-end consome
via Server-Sent Events:

    {"tipo": "inicio", "etapas": [{"id", "rotulo"}], "versao", "tema"}
    {"tipo": "etapa", "id", "status": "iniciada"|"concluida"|"erro", "duracao_s"?}
    {"tipo": "tentativa", "id", "atual", "maximo"}      # iterações do loop de apuração
    {"tipo": "conteudo", "markdown"}
    {"tipo": "erro", "mensagem"}
    {"tipo": "cancelado", "mensagem"}                   # emitido na hora em que o usuário cancela
    {"tipo": "fim", "duracao_s", "cancelada"}
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from agno.run.cancel import cancel_run, get_active_runs

from agente.comum import mensagem_erro_amigavel
from agente.passos import CONTROLE_EXECUCAO, novo_run_id

ROTULOS = {
    "pesquisa": "Pesquisa",
    "apuracao": "Apuração",
    "apuracao_loop": "Apuração (loop)",
    "validacao_fontes": "Validação de fontes",
    "verificacao": "Fact check",
    "analise_mercado": "Análise de mercado",
    "consolidacao": "Consolidação",
    "redacao": "Redação",
    "exportacao": "Exportação",
    "agente": "Agente único",
}

INICIO = {"StepStartedEvent", "LoopExecutionStartedEvent"}
CONCLUSAO = {"StepCompletedEvent", "LoopExecutionCompletedEvent"}


def etapas_do_executor(executor: Any) -> list[dict]:
    """Etapas de primeiro nível do workflow (ou uma etapa só, para um agente)."""
    passos = getattr(executor, "steps", None)
    if not passos:
        return [{"id": "agente", "rotulo": ROTULOS["agente"]}]
    return [{"id": p.name, "rotulo": ROTULOS.get(p.name, p.name)} for p in passos]


def cancelar_run_do_agno(run_id: str, prazo: float = 10.0) -> None:
    """Cancela um run do Agno, mesmo que ele ainda não tenha começado.

    O gerenciador do Agno ignora runs desconhecidos e o `register_run` (feito
    pelo próprio agente ao iniciar) zera o estado. Por isso, se o run ainda não
    foi registrado, uma thread curta espera o registro e então cancela.
    """
    if run_id in get_active_runs():
        cancel_run(run_id)
        return

    def esperar_e_cancelar() -> None:
        limite = time.time() + prazo
        while time.time() < limite:
            if run_id in get_active_runs():
                cancel_run(run_id)
                return
            time.sleep(0.05)

    threading.Thread(target=esperar_e_cancelar, daemon=True, name=f"cancelar-{run_id[:8]}").start()


@dataclass
class Tarefa:
    tema: str
    versao: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    eventos: list[dict] = field(default_factory=list)
    concluida: bool = False
    cancelada: bool = False
    criada_em: float = field(default_factory=time.time)
    run_ids: list[str] = field(default_factory=list)
    _trava: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def emitir(self, evento: dict) -> None:
        with self._trava:
            self.eventos.append(evento)

    def registrar_run(self, run_id: str) -> None:
        """Chamado pelos passos (agente.passos.novo_run_id) a cada agente disparado."""
        with self._trava:
            self.run_ids.append(run_id)
            cancelada = self.cancelada
        if cancelada:  # cancelaram enquanto o passo começava
            cancelar_run_do_agno(run_id)

    def cancelar(self) -> bool:
        """Pede o cancelamento. Retorna False se a tarefa já tinha terminado ou sido cancelada."""
        with self._trava:
            if self.concluida or self.cancelada:
                return False
            self.cancelada = True
            run_ids = list(self.run_ids)
            self.eventos.append({"tipo": "cancelado", "mensagem": "Pesquisa cancelada pelo usuário."})
        for run_id in run_ids:  # interrompe os agentes em execução entre as chamadas ao modelo
            cancelar_run_do_agno(run_id)
        return True


    def eventos_desde(self, indice: int) -> list[dict]:
        with self._trava:
            return list(self.eventos[indice:])

    def resumo(self) -> dict:
        with self._trava:
            eventos = list(self.eventos)
        conteudo = next((e["markdown"] for e in reversed(eventos) if e["tipo"] == "conteudo"), None)
        erro = next((e["mensagem"] for e in reversed(eventos) if e["tipo"] == "erro"), None)
        return {
            "id": self.id,
            "tema": self.tema,
            "versao": self.versao,
            "concluida": self.concluida,
            "cancelada": self.cancelada,
            "conteudo": conteudo,
            "erro": erro,
            "eventos": eventos,
        }


def executar(tarefa: Tarefa, executor: Any) -> None:
    """Roda o executor e emite os eventos da tarefa (bloqueante; use numa thread)."""
    inicio = time.time()
    etapas = etapas_do_executor(executor)
    ids = {e["id"] for e in etapas}
    iniciadas: dict[str, float] = {}
    tarefa.emitir({"tipo": "inicio", "etapas": etapas, "versao": tarefa.versao, "tema": tarefa.tema})

    def concluir_etapa(etapa_id: str, status: str = "concluida") -> None:
        duracao = round(time.time() - iniciadas.get(etapa_id, time.time()), 1)
        tarefa.emitir({"tipo": "etapa", "id": etapa_id, "status": status, "duracao_s": duracao})

    token = CONTROLE_EXECUCAO.set(tarefa)  # os passos registram seus run_ids e checam o cancelamento
    try:
        if getattr(executor, "steps", None):
            conteudo = None
            eventos = executor.run(tarefa.tema, stream=True, stream_events=True)
            for evento in eventos:
                if tarefa.cancelada:
                    _fechar(eventos)  # não avança para as próximas etapas (nem salva a matéria)
                    break
                nome = type(evento).__name__
                etapa_id = getattr(evento, "step_name", None)
                if nome in INICIO and etapa_id in ids and etapa_id not in iniciadas:
                    iniciadas[etapa_id] = time.time()
                    tarefa.emitir({"tipo": "etapa", "id": etapa_id, "status": "iniciada"})
                elif nome in CONCLUSAO and etapa_id in ids:
                    concluir_etapa(etapa_id)
                elif nome == "LoopIterationStartedEvent" and etapa_id in ids:
                    tarefa.emitir({"tipo": "tentativa", "id": etapa_id, "atual": evento.iteration,
                                   "maximo": evento.max_iterations})
                elif nome == "StepErrorEvent" and etapa_id in ids:
                    concluir_etapa(etapa_id, "erro")
                elif nome == "WorkflowErrorEvent":
                    raise RuntimeError(getattr(evento, "error", None) or "falha no workflow")
                elif nome == "WorkflowCompletedEvent":
                    conteudo = getattr(evento, "content", None)
            if tarefa.cancelada:
                return
            if not conteudo:
                raise RuntimeError("o workflow terminou sem conteúdo")
        else:
            iniciadas["agente"] = time.time()
            tarefa.emitir({"tipo": "etapa", "id": "agente", "status": "iniciada"})
            resultado = executor.run(tarefa.tema, stream=False, run_id=novo_run_id())
            if tarefa.cancelada:
                return
            conteudo = getattr(resultado, "content", None)
            if "ERROR" in str(getattr(resultado, "status", "")).upper() or not conteudo:
                concluir_etapa("agente", "erro")
                raise RuntimeError(conteudo or "o agente terminou sem conteúdo")
            concluir_etapa("agente")
        tarefa.emitir({"tipo": "conteudo", "markdown": str(conteudo)})
    except Exception as erro:  # noqa: BLE001 - qualquer falha vira evento para o usuário
        if not tarefa.cancelada:  # falhas causadas pelo próprio cancelamento não são erro
            tarefa.emitir({"tipo": "erro", "mensagem": mensagem_erro_amigavel(str(erro))})
    finally:
        CONTROLE_EXECUCAO.reset(token)
        tarefa.emitir({"tipo": "fim", "duracao_s": round(time.time() - inicio, 1), "cancelada": tarefa.cancelada})
        tarefa.concluida = True


def _fechar(gerador: Any) -> None:
    try:
        gerador.close()
    except Exception:  # noqa: BLE001 - o Agno pode levantar ao interromper o stream
        pass


class GerenciadorDeTarefas:
    """Guarda as tarefas em memória e dispara cada uma numa thread."""

    def __init__(self, max_tarefas: int = 50):
        self._tarefas: dict[str, Tarefa] = {}
        self._trava = threading.Lock()
        self._max = max_tarefas

    def criar(self, tema: str, versao: str, executor: Any) -> Tarefa:
        tarefa = Tarefa(tema=tema, versao=versao)
        with self._trava:
            self._tarefas[tarefa.id] = tarefa
            # Descarta as tarefas concluídas mais antigas
            concluidas = sorted((t for t in self._tarefas.values() if t.concluida), key=lambda t: t.criada_em)
            for antiga in concluidas[: max(0, len(self._tarefas) - self._max)]:
                self._tarefas.pop(antiga.id, None)
        threading.Thread(target=executar, args=(tarefa, executor), daemon=True, name=f"tarefa-{tarefa.id}").start()
        return tarefa

    def obter(self, tarefa_id: str) -> Tarefa | None:
        with self._trava:
            return self._tarefas.get(tarefa_id)

    def em_andamento(self) -> int:
        with self._trava:
            return sum(1 for t in self._tarefas.values() if not t.concluida)
