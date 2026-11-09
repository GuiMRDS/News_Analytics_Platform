"""Registro das versões dos agentes expostas pela API.

Cada versão é importada sob demanda (lazy), para não instanciar os agentes
de todas as versões ao subir o servidor.
"""

from dataclasses import asdict, dataclass
from functools import lru_cache
from importlib import import_module
from typing import Any


@dataclass(frozen=True)
class Versao:
    chave: str
    rotulo: str
    modulo: str
    objeto: str
    descricao: str
    pipeline: str

    def publico(self) -> dict:
        dados = asdict(self)
        dados.pop("modulo")
        dados.pop("objeto")
        return dados


VERSOES: dict[str, Versao] = {
    "V5": Versao(
        chave="V5",
        rotulo="V5 · Investidor",
        modulo="agente.agente_curador_v5",
        objeto="investor_workflow",
        descricao="Foco em mercado financeiro: equipe de pesquisa (Brasil + global), apuração, "
        "fact checking com dados reais, analista de investimentos (cotações B3, Selic, CDI, IPCA, "
        "dólar) e matéria com a seção 'O que isso significa para o investidor'.",
        pipeline="Research Team → Apuração (loop) → Validação → Fact Check → Análise de Mercado → Redação → Markdown",
    ),
    "V4": Versao(
        chave="V4",
        rotulo="V4 · Multi-Agent Research",
        modulo="agente.agente_curador_v4",
        objeto="research_pipeline_workflow",
        descricao="Equipe de pesquisa (nacional + internacional), loop de apuração, validação de fontes, "
        "fact checking, redação e exportação Markdown.",
        pipeline="Research Team → Apuração (loop) → Validação → Fact Check → Redação → Markdown",
    ),
    "V3": Versao(
        chave="V3",
        rotulo="V3 · Loop + Fact Check",
        modulo="agente.agente_curador_v3",
        objeto="news_curator_workflow",
        descricao="Workflow com loop de apuração até atingir o mínimo de fontes.",
        pipeline="Pesquisa → Apuração (loop) → Verificação → Redação",
    ),
    "V2": Versao(
        chave="V2",
        rotulo="V2 · Workflow",
        modulo="agente.agente_curador_v2",
        objeto="workflow",
        descricao="Quatro agentes especializados em sequência.",
        pipeline="Pesquisador → Apurador → Verificador → Redator",
    ),
    "V1": Versao(
        chave="V1",
        rotulo="V1 · Agente único",
        modulo="agente.agente_curador",
        objeto="agente_noticias",
        descricao="Um único agente executa todas as etapas.",
        pipeline="Agente Jornalista → Matéria",
    ),
}

VERSAO_PADRAO = "V5"


@lru_cache(maxsize=None)
def carregar_workflow(chave: str) -> Any:
    """Importa e devolve o agente/workflow da versão (com cache)."""
    versao = VERSOES[chave]
    return getattr(import_module(versao.modulo), versao.objeto)
