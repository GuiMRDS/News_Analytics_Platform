"""V4 — Multi-Agent Research Pipeline.

Research Team -> Apuração (loop) -> Validação de Fontes -> Fact Checking
-> Redação -> Exportação Markdown
"""

import re
import unicodedata
from datetime import date
from typing import List

from agno.agent import Agent
from agno.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.workflow import Workflow, Step, Loop
from agno.workflow.types import StepInput, StepOutput

from agente.comum import (
    BASE_DIR,
    carregar_skills,
    contar_fontes,
    criar_modelo,
    diretorio_saida,
    verificar_api_key,
)

VERSAO = "V4"
MIN_FONTES = 3
MAX_TENTATIVAS_APURACAO = 3

shared_skills = carregar_skills()
output_dir = diretorio_saida(VERSAO)


# ---------------------------------------------------------------------------
# Research Team
# ---------------------------------------------------------------------------

pesquisador_nacional = Agent(
    name="Pesquisador Nacional",
    role="Busca notícias recentes sobre o tema em veículos brasileiros.",
    model=criar_modelo(),
    skills=shared_skills,
    instructions=[
        "Você é um pesquisador de notícias focado em veículos brasileiros.",
        "Antes de começar, carregue as instruções da skill usando get_skill_instructions.",
        "Execute a skill 'pesquisa-noticias' pesquisando em português.",
        "Inclua veículo e URL completa de cada notícia encontrada.",
    ],
    tools=[DuckDuckGoTools()],
    add_datetime_to_context=True,
    markdown=True,
)

pesquisador_internacional = Agent(
    name="Pesquisador Internacional",
    role="Busca notícias recentes sobre o tema em agências e veículos internacionais.",
    model=criar_modelo(),
    skills=shared_skills,
    instructions=[
        "Você é um pesquisador de notícias focado em agências e veículos internacionais (Reuters, AP, AFP, BBC etc.).",
        "Antes de começar, carregue as instruções da skill usando get_skill_instructions.",
        "Execute a skill 'pesquisa-noticias' pesquisando em inglês e português.",
        "Inclua veículo e URL completa de cada notícia encontrada.",
    ],
    tools=[DuckDuckGoTools()],
    add_datetime_to_context=True,
    markdown=True,
)

research_team = Team(
    name="Research Team",
    model=criar_modelo(),
    members=[pesquisador_nacional, pesquisador_internacional],
    delegate_to_all_members=True,
    instructions=[
        "Você é o líder da equipe de pesquisa.",
        "Delegue a pesquisa do tema a todos os membros e consolide os resultados.",
        "Escolha a notícia principal (a mais relevante e atual) considerando os dois levantamentos.",
        "Retorne exatamente: **Título**, **Resumo** (2-3 frases), **Fonte** e **Palavras-chave**.",
        "Ao final, liste todas as fontes encontradas pelos membros no formato: - **Nome do Veículo**: Título (URL).",
    ],
    add_datetime_to_context=True,
    markdown=True,
)


# ---------------------------------------------------------------------------
# Agentes das demais etapas
# ---------------------------------------------------------------------------

apurador = Agent(
    name="Apurador de Fontes",
    model=criar_modelo(),
    skills=shared_skills,
    instructions=[
        "Você é um apurador de fontes jornalísticas.",
        "Antes de começar, carregue as instruções da skill usando get_skill_instructions.",
        "Receba a saída da equipe de pesquisa e execute a skill 'apuracao-fontes'.",
        f"IMPORTANTE: Você DEVE encontrar no mínimo {MIN_FONTES} fontes distintas.",
        "Na seção '## FONTES COLETADAS', SEMPRE inclua o nome do veículo em negrito e a URL completa.",
        "Use o formato: - **Nome do Veículo**: Título da matéria (URL)",
        "Se a apuração anterior não atingiu o mínimo, busque fontes DIFERENTES das já encontradas.",
        "Tente outros veículos, agências internacionais (Reuters, AP, AFP) e portais variados.",
        "Pesquise em inglês e português para ampliar o alcance de fontes.",
    ],
    tools=[DuckDuckGoTools()],
    add_datetime_to_context=True,
    markdown=True,
)

verificador = Agent(
    name="Verificador Factual",
    model=criar_modelo(),
    skills=shared_skills,
    instructions=[
        "Você é um verificador factual.",
        "Antes de começar, carregue as instruções da skill usando get_skill_instructions.",
        "Receba o dossiê validado e execute a skill 'verificacao-factual'.",
        "Leve em conta o resultado da '## VALIDAÇÃO DE FONTES' no início do dossiê.",
        "Preserve veículos e URLs de todas as fontes para uso do redator.",
    ],
    tools=[DuckDuckGoTools()],
    add_datetime_to_context=True,
    markdown=True,
)

redator = Agent(
    name="Redator",
    model=criar_modelo(),
    skills=shared_skills,
    instructions=[
        "Você é um redator jornalístico profissional.",
        "Antes de começar, carregue as instruções da skill usando get_skill_instructions.",
        "Receba o relatório do verificador e execute a skill 'redacao-jornalistica'.",
        f"Se o relatório indicar menos de {MIN_FONTES} fontes independentes, inclua um aviso claro no início da matéria: '⚠️ NOTA: Esta matéria foi produzida com um número limitado de fontes independentes.'",
        "IMPORTANTE: Ao citar qualquer dado, fato ou informação de uma fonte, insira a referência numérica [1], [2], [3] etc. no corpo do texto.",
        "IMPORTANTE: No final da matéria, inclua uma seção '## Referências' com a lista numerada de todas as fontes, incluindo nome do veículo, título e URL completa.",
        "Responda APENAS com a matéria em Markdown; o arquivo será salvo automaticamente pela etapa de exportação.",
    ],
    add_datetime_to_context=True,
    markdown=True,
)


# ---------------------------------------------------------------------------
# Funções do workflow
# ---------------------------------------------------------------------------

def fontes_suficientes(outputs: List[StepOutput]) -> bool:
    """Condição de parada do loop de apuração: atingiu MIN_FONTES?"""
    if not outputs:
        return False
    return contar_fontes(str(outputs[-1].content or "")) >= MIN_FONTES


def validar_fontes(step_input: StepInput) -> StepOutput:
    """Valida (sem LLM) a quantidade de fontes do dossiê e anota o resultado."""
    dossie = str(step_input.previous_step_content or "")
    total = contar_fontes(dossie)

    if total >= MIN_FONTES:
        status = f"✅ APROVADO — {total} fontes distintas (mínimo {MIN_FONTES})."
    else:
        status = (
            f"⚠️ INSUFICIENTE — apenas {total} fontes distintas (mínimo {MIN_FONTES}) "
            f"após {MAX_TENTATIVAS_APURACAO} tentativas de apuração. "
            "O redator deve incluir a nota de fontes limitadas."
        )

    return StepOutput(content=f"## VALIDAÇÃO DE FONTES\n\n{status}\n\n{dossie}")


def _slug(texto: str, limite: int = 50) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^a-zA-Z0-9]+", "_", texto).strip("_").lower()
    return texto[:limite].rstrip("_") or "materia"


def exportar_markdown(step_input: StepInput) -> StepOutput:
    """Salva a matéria final em output/V4/materia_<tema>_<data>.md."""
    materia = str(step_input.previous_step_content or "").strip()
    tema = step_input.get_input_as_string() or "materia"

    arquivo = output_dir / f"materia_{_slug(tema)}_{date.today().isoformat()}.md"
    arquivo.write_text(materia + "\n", encoding="utf-8")

    caminho = arquivo.relative_to(BASE_DIR).as_posix()
    return StepOutput(content=f"{materia}\n\n---\n_Matéria salva em `{caminho}`_")


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

pesquisa_step = Step(
    name="pesquisa",
    description="Research Team: pesquisa nacional e internacional consolidada",
    team=research_team,
)

apuracao_loop = Loop(
    name="apuracao_loop",
    description="Repete a apuração até atingir o mínimo de fontes",
    steps=[
        Step(
            name="apuracao",
            description="Apuração multi-fonte",
            agent=apurador,
        )
    ],
    max_iterations=MAX_TENTATIVAS_APURACAO,
    end_condition=fontes_suficientes,
)

validacao_step = Step(
    name="validacao_fontes",
    description="Valida a quantidade mínima de fontes",
    executor=validar_fontes,
)

verificacao_step = Step(
    name="verificacao",
    description="Verificação factual do dossiê",
    agent=verificador,
)

redacao_step = Step(
    name="redacao",
    description="Redação jornalística final",
    agent=redator,
)

exportacao_step = Step(
    name="exportacao",
    description="Exporta a matéria para Markdown",
    executor=exportar_markdown,
)

research_pipeline_workflow = Workflow(
    name="Multi-Agent Research Pipeline",
    description=(
        "Research Team -> Apuração (loop) -> Validação de Fontes -> "
        "Fact Checking -> Redação -> Markdown"
    ),
    steps=[
        pesquisa_step,
        apuracao_loop,
        validacao_step,
        verificacao_step,
        redacao_step,
        exportacao_step,
    ],
)


if __name__ == "__main__":
    verificar_api_key()
    research_pipeline_workflow.print_response(
        "Quem é Gustavo Guanabara?",
        stream=True,
    )
