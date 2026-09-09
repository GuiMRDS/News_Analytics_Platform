import os

from pathlib import Path

from agno.agent import Agent
from agno.models.groq import Groq
from agno.skills import Skills, LocalSkills
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.file import FileTools
from agno.workflow import Workflow
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

output_dir = Path(__file__).parent / "output/V0"
file_tools = FileTools(
    base_dir=output_dir,
    enable_save_file=True,
    enable_read_file=True,
    enable_list_files=True,
)

skills_dir = Path(__file__).parent / "skills"
shared_skills = Skills(
    loaders=[
        LocalSkills(str(skills_dir)),
    ]
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

apurador = Agent(
    name="Apurador de Fontes",
    model = Groq(id="openai/gpt-oss-20b",api_key=GROQ_API_KEY),
    skills=shared_skills,
    instructions=[
         "Você é um apurador de fontes jornalísticas.",
        "Antes de começar, carregue as instruções da skill usando get_skill_instructions.",
        "Receba a saída do pesquisador e execute a skill 'apuracao-fontes'.",
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
        "IMPORTANTE: Ao citar qualquer dado, fato ou informação de uma fonte, insira a referência numérica [1], [2], [3] etc. no corpo do texto.",
        "IMPORTANTE: No final da matéria, inclua uma seção '## Referências' com a lista numerada de todas as fontes, incluindo nome do veículo, título e URL completa.",
        "Ao finalizar a redação, salve o conteúdo em um arquivo usando a ferramenta de arquivos.",
    ],
    tools=[file_tools],
    add_datetime_to_context=True,
    markdown=True,
)

workflow = Workflow(
    name="Curador de Noticias com Workflow",
    description="Pesquisa, apura, verifica e redige matéria final",
    steps=[pesquisador, apurador, verificador, redator],
)


if __name__ == "__main__":
    workflow.print_response(
        "Quem é Gustavo Guanabara?",
        stream=True
    )