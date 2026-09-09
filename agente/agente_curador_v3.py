import os
import re
from typing import List
from pathlib import Path
from dotenv import load_dotenv
from newspaper import urls

load_dotenv()

from agno.agent import Agent
from agno.team import Team
from agno.models.groq import Groq
from agno.skills import Skills, LocalSkills
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.file import FileTools
from agno.workflow import Workflow, Step, Loop
from agno.workflow.types import StepOutput



GROQ_API_KEY = os.getenv("GROQ_API_KEY")

MIN_FONTES = 3
MAX_TENTATIVAS_APURACAO = 3

skills_dir = Path(__file__).parent / "skills"
shared_skills = Skills(
    loaders=[
        LocalSkills(str(skills_dir)),
    ]
)

output_dir = Path(__file__).parent / "output/V2"
output_dir.mkdir(parents=True, exist_ok=True)
file_tools = FileTools(
    base_dir=output_dir,
    enable_save_file=True,
    enable_read_file=True,
    enable_list_files=True,
)


pesquisador = Agent(
    name="Pesquisador",
    model = Groq(id="openai/gpt-oss-20b",api_key=GROQ_API_KEY),
    skills=shared_skills,
    instructions=[
        "Você é um pesquisador de notícias.",
        "Antes de começar, carregue as instruções da skill usando get_skill_instructions.",
        "Execute a skill 'pesquisa-noticias' e retorne exatamente no formato definido nela.",
        "Salve o resultado da pesquisa em um arquivo usando a ferramenta de arquivos.",
    ],
    tools=[DuckDuckGoTools(), file_tools],
    add_datetime_to_context=True,
    markdown=True,
)

time_research = Agent(
    name="Research",
    model = Groq(id="openai/gpt-oss-20b",api_key=GROQ_API_KEY),
    skills=shared_skills,
    instructions=[
        "Você é o líder da equipe de pesquisa.",
        "Sua missão é coordenar a busca por notícias relevantes e recentes sobre o tema solicitado.",
        "Garanta que o pesquisador utilize a skill 'pesquisa-noticias' corretamente.",
        "O objetivo final é fornecer um conjunto rico de informações para as etapas seguintes de apuração e verificação.",
        "Certifique-se de que os resultados sejam salvos corretamente em arquivo.",
    ],
    add_datetime_to_context=True,
    markdown=True,
)

apurador = Agent(
    name="Apurador de Fontes",
    model = Groq(id="openai/gpt-oss-20b",api_key=GROQ_API_KEY),
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
    tools=[DuckDuckGoTools(), file_tools],
    add_datetime_to_context=True,
    markdown=True,
)

verificador = Agent(
    name="verificador Factual",
    model = Groq(id="openai/gpt-oss-20b",api_key=GROQ_API_KEY),
    skills=shared_skills,
    instructions=[
        "Você é um verificador factual.",
        "Antes de começar, carregue as instruções da skill usando get_skill_instructions.",
        "Receba o dossiê do apurador e execute a skill 'verificacao-factual'.",
        "Salve o resultado da verificação em um arquivo usando a ferramenta de arquivos.",
    ],
    tools=[DuckDuckGoTools(), file_tools],
    add_datetime_to_context=True,
    markdown=True,
)

redator = Agent(
    name="Redator",
    model = Groq(id="openai/gpt-oss-20b",api_key=GROQ_API_KEY),
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


def contar_fontes(texto: str) -> int:
    """
        Função Auxiliar: Extração e contagem analítica

        Analisa o texto retornado pelo agente Apurador para contar o número
        de fontes distintas que ele conseguiu encontrar. Para garantir que
        não estejamos contando fontes repetidas apenas pelo título da seção,
        usamos expressões regulares (Regex) para varrer o texto.

        Como funciona:
        1. Isola a seção específica ("FONTES COLETADAS") do dossiê.
        2. Conta quantos itens formatados em Markdown (ex: "- **Veículo**") existem.
        3. Conta quantos links web (URLs ou http/https) distintos existem no texto.
        4. Retorna o maior número entre as duas contagens (garantimos assim o pior caso).
    """

    secao = texto
    match = re.search(
        r"##\s*FONTES COLETADAS(.*?)(##|$)", texto, re.DOTALL | re.IGNORECASE
    )
    if match:
        secao = match.group(1)


    fontes_por_marcador = re.findall(r"^-\s+\*\*", secao, re.MULTILINE)

    return max(len(fontes_por_marcador), len(urls))

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



pesquisa_step = Step(
    name="pesquisa",
    description="Pesquisa de notícias sobre o tema",
    team=time_research,
)

apuracao_step = Step(
    name="apuracao",
    description="Apuração multi-fonte com verificação de fontes",
    agent=apurador,
)

apuracao_loop = Loop(
    name="apuracao_loop",
    description="Repete a apuração até atingir o mínimo de fontes",
    steps=[apuracao_step],
    max_iterations=MAX_TENTATIVAS_APURACAO,
    end_condition=fontes_suficientes,
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


news_curator_workflow = Workflow(
    name="News Curator Pipeline",
    description="Pesquisa -> Apuração (loop) -> Verificação Factual -> Redação",
    steps=[pesquisa_step, apuracao_loop, verificacao_step, redacao_step],
)

if __name__ == "__main__":
    news_curator_workflow.print_response(
        "Quem é Gustavo Guanabara?",
        stream=True
    )