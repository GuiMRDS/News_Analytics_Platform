from typing import List

from agno.agent import Agent
from agno.workflow import Workflow, Loop
from agno.workflow.types import StepOutput

from agente.passos import passo_agente
from agente.comum import (
    criar_busca,
    carregar_skills,
    contar_fontes,
    criar_file_tools,
    criar_modelo,
    verificar_api_key,
)

MIN_FONTES = 3
MAX_TENTATIVAS_APURACAO = 3

shared_skills = carregar_skills()
file_tools = criar_file_tools("V3")


pesquisador = Agent(
    name="Pesquisador",
    model=criar_modelo(),
    skills=shared_skills,
    instructions=[
        "Você é um pesquisador de notícias.",
        "Antes de começar, carregue as instruções da skill usando get_skill_instructions.",
        "Execute a skill 'pesquisa-noticias' e retorne exatamente no formato definido nela.",
        "Salve o resultado da pesquisa em um arquivo usando a ferramenta de arquivos.",
    ],
    tools=[criar_busca(), file_tools],
    add_datetime_to_context=True,
    markdown=True,
)

apurador = Agent(
    name="Apurador de Fontes",
    model=criar_modelo(),
    skills=shared_skills,
    instructions=[
        "Você é um apurador de fontes jornalísticas.",
        "Antes de começar, carregue as instruções da skill usando get_skill_instructions.",
        "Receba a saída do pesquisador e execute a skill 'apuracao-fontes'.",
        f"IMPORTANTE: Você DEVE encontrar no mínimo {MIN_FONTES} fontes distintas.",
        "Para cada fonte, SEMPRE inclua o nome do veículo em negrito e a URL completa.",
        "Use o formato: - **Nome do Veículo**: Título da matéria (URL)",
        "Se a apuração anterior não atingiu o mínimo, busque fontes DIFERENTES das já encontradas.",
        "Tente outros veículos, agências internacionais (Reuters, AP, AFP) e portais variados.",
        "Pesquise em inglês e português para ampliar o alcance de fontes.",
        "Salve o resultado da apuração em um arquivo usando a ferramenta de arquivos.",
    ],
    tools=[criar_busca(), file_tools],
    add_datetime_to_context=True,
    markdown=True,
)

verificador = Agent(
    name="verificador Factual",
    model=criar_modelo(),
    skills=shared_skills,
    instructions=[
        "Você é um verificador factual.",
        "Antes de começar, carregue as instruções da skill usando get_skill_instructions.",
        "Receba o dossiê do apurador e execute a skill 'verificacao-factual'.",
        "Salve o resultado da verificação em um arquivo usando a ferramenta de arquivos.",
    ],
    tools=[criar_busca(), file_tools],
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
        "OBRIGATÓRIO: Ao finalizar a redação, você DEVE salvar a matéria completa em um arquivo Markdown (.md) usando a ferramenta save_file.",
        "Use o nome de arquivo no formato: materia_<tema_resumido>_<data_YYYY-MM-DD>.md (ex: materia_economia_brasileira_2026-02-10.md).",
        "Nunca termine sem salvar o arquivo. Confirme o nome do arquivo salvo na sua resposta final.",
    ],
    tools=[file_tools],
    add_datetime_to_context=True,
    markdown=True,
)


def fontes_suficientes(outputs: List[StepOutput]) -> bool:
    """
        Função Condição de Parada (End Condition): Validando o Loop

        É utilizada como instrução na etapa de loop da apuração (apuracao_loop).
        Esta função avalia a última resposta (outputs[-1]) obtida e valida
        se atende a regra de negócio da nossa redação: atingir um número
        mínimo predeterminado de fontes.

        Funcionamento do fluxo na prática:
        - O Loop de apuração executa a sua tarefa usando o agente correspondente.
        - Essa condição (fontes_suficientes) é executada em seguida por fora,
          injetando os retornos 'outputs' da execução.
        - Se retornar 'True', o agente atendeu a meta e prossegue para a Verificação Factual.
        - Se retornar 'False', a etapa de apuração ocorre novamente.

        Args:
            outputs (List[StepOutput]): Histórico de respostas/etapas do Workflow anterior
        Returns:
            bool: Retorna True se atingiu ou ultrapassou MIN_FONTES, senão False.
    """

    if not outputs:
        return False

    latest = outputs[-1]
    content = str(latest.content or "")

    return contar_fontes(content) >= MIN_FONTES



pesquisa_step = passo_agente("pesquisa", pesquisador, "Pesquisa de notícias sobre o tema")

apuracao_step = passo_agente("apuracao", apurador, "Apuração multi-fonte com verificação de fontes")

apuracao_loop = Loop(
    name="apuracao_loop",
    description="Repete a apuração até atingir o mínimo de fontes",
    steps=[apuracao_step],
    max_iterations=MAX_TENTATIVAS_APURACAO,
    end_condition=fontes_suficientes,
)

verificacao_step = passo_agente("verificacao", verificador, "Verificação factual do dossiê")

redacao_step = passo_agente("redacao", redator, "Redação jornalística final")


news_curator_workflow = Workflow(
    name="News Curator Pipeline",
    description="Pesquisa -> Apuração (loop) -> Verificação Factual -> Redação",
    steps=[pesquisa_step, apuracao_loop, verificacao_step, redacao_step],
)

if __name__ == "__main__":
    verificar_api_key()
    news_curator_workflow.print_response(
        "Quem é Gustavo Guanabara?",
        stream=True
    )