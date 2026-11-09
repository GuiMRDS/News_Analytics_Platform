# ui/registry.py
"""Registro das versões do curador exibidas na UI.

Cada versão é importada sob demanda (lazy), para não instanciar os agentes
de todas as versões ao abrir a interface.
"""

from dataclasses import dataclass
from functools import lru_cache
from importlib import import_module
from typing import Any


@dataclass(frozen=True)
class Versao:
    rotulo: str
    modulo: str
    objeto: str
    descricao: str
    pipeline: str


VERSOES: dict[str, Versao] = {
    "V5": Versao(
        rotulo="V5 - Investidor",
        modulo="agente.agente_curador_v5",
        objeto="investor_workflow",
        descricao="Foco em mercado financeiro: equipe de pesquisa (Brasil + global), apuração, "
        "fact checking com dados reais, analista de investimentos (cotações B3, Selic, CDI, IPCA, "
        "dólar) e matéria com a seção 'O que isso significa para o investidor'.",
        pipeline="Research Team → Apuração (loop) → Validação → Fact Check → Análise de Mercado → Redação → Markdown",
    ),
    "V4": Versao(
        rotulo="V4 - Multi-Agent Research Pipeline",
        modulo="agente.agente_curador_v4",
        objeto="research_pipeline_workflow",
        descricao="Equipe de pesquisa (nacional + internacional), loop de apuração, "
        "validação de fontes, fact checking, redação e exportação Markdown.",
        pipeline="Research Team → Apuração (loop) → Validação → Fact Check → Redação → Markdown",
    ),
    "V3": Versao(
        rotulo="V3 - Loop + Fact Check",
        modulo="agente.agente_curador_v3",
        objeto="news_curator_workflow",
        descricao="Workflow com loop de apuração até atingir o mínimo de fontes.",
        pipeline="Pesquisa → Apuração (loop) → Verificação → Redação",
    ),
    "V2": Versao(
        rotulo="V2 - Workflow",
        modulo="agente.agente_curador_v2",
        objeto="workflow",
        descricao="Quatro agentes especializados em sequência.",
        pipeline="Pesquisador → Apurador → Verificador → Redator",
    ),
    "V1": Versao(
        rotulo="V1 - Agent Único",
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
