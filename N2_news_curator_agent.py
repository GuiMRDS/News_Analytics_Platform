# =============================================================================
# N2 — Equipe de Notícias (Nível 2: Workflow de Agentes)
# =============================================================================
#
# Este script cria um WORKFLOW que orquestra uma equipe de 4 AGENTES especializados.
# Diferente do Nível 0 (agente único), aqui temos especialistas colaborando:
#
#   [Pesquisador] → [Apurador] → [Verificador] → [Redator] → Matéria Final
#
# Conceitos praticados neste nível:
#   • Workflows    — cadeias de execução controlada (Pipeline)
#   • Multi-Agent  — sistemas com múltiplos agentes especialistas
#   • Role-playing — cada agente foca exclusivamente em sua função
#   • Shared Skills— habilidades compartilhadas carregadas de arquivos externos
# =============================================================================


# ─────────────────────────────────────────────────────────────────────────────
# 1. IMPORTAÇÕES
#    Além das básicas, importamos:
#    - Workflow     → para criar a cadeia de execução
#    - Skills, LocalSkills → para carregar skills de arquivos externos
# ─────────────────────────────────────────────────────────────────────────────
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from agno.skills import Skills, LocalSkills
from agno.workflow import Workflow
from agno.tools.websearch import WebSearchTools
from agno.tools.file import FileTools

# ─────────────────────────────────────────────────────────────────────────────
# 2. CONFIGURAÇÃO E SKILLS COMPARTILHADAS
#    Neste nível, as skills não estão no prompt (como no N0), mas em arquivos
#    na pasta /skills. Isso permite reuso e organização.
#    
#    Carregamos as skills locais e configuramos o diretório de saída.
# ─────────────────────────────────────────────────────────────────────────────
# Filetools
output_dir = Path(__file__).parent / "output/N2/"
file_tools = FileTools(
    base_dir=output_dir,
    enable_save_file=True,
    enable_read_file=True,
    enable_list_files=True,
)

# Skills
skills_dir = Path(__file__).parent / "skills"
shared_skills = Skills(
    loaders=[
        LocalSkills(str(skills_dir)),
    ]
)

# ─────────────────────────────────────────────────────────────────────────────
# 3. CRIAÇÃO DOS AGENTES ESPECIALISTAS
#    Criamos 4 agentes, cada um com um "role" (papel) específico.
#    Eles usam o mesmo 'shared_skills', mas recebem instruções focadas.
# ─────────────────────────────────────────────────────────────────────────────

# 1) Pesquisador — usa a skill de pesquisa de notícias
pesquisador = Agent(
    name="Pesquisador",
    model=OpenAIResponses(id="gpt-5-nano", api_key=os.getenv("OPENAI_API_KEY")),
    skills=shared_skills,
    instructions=[
        "Você é um pesquisador de notícias.",
        "Antes de começar, carregue as instruções da skill usando get_skill_instructions.",
        "Execute a skill 'pesquisa-noticias' e retorne exatamente no formato definido nela.",
        "Salve o resultado da pesquisa em um arquivo usando a ferramenta de arquivos.",
    ],
    tools=[WebSearchTools(), file_tools],
    add_datetime_to_context=True,
    markdown=True,
)

# 2) Apurador de Fontes — usa a skill de apuração multi-fonte
apurador = Agent(
    name="Apurador de Fontes",
    model=OpenAIResponses(id="gpt-5-nano", api_key=os.getenv("OPENAI_API_KEY")),
    skills=shared_skills,
    instructions=[
        "Você é um apurador de fontes jornalísticas.",
        "Antes de começar, carregue as instruções da skill usando get_skill_instructions.",
        "Receba a saída do pesquisador e execute a skill 'apuracao-fontes'.",
        "Salve o resultado da apuração em um arquivo usando a ferramenta de arquivos.",
    ],
    tools=[WebSearchTools(), file_tools],
    add_datetime_to_context=True,
    markdown=True,
)

# 3) Verificador Factual — usa a skill de fact-checking
verificador = Agent(
    name="Verificador Factual",
    model=OpenAIResponses(id="gpt-5-nano", api_key=os.getenv("OPENAI_API_KEY")),
    skills=shared_skills,
    instructions=[
        "Você é um verificador factual.",
        "Antes de começar, carregue as instruções da skill usando get_skill_instructions.",
        "Receba o dossiê do apurador e execute a skill 'verificacao-factual'.",
        "Salve o resultado da verificação em um arquivo usando a ferramenta de arquivos.",
    ],
    tools=[WebSearchTools(), file_tools],
    add_datetime_to_context=True,
    markdown=True,
)

# 4) Redator — usa a skill de redação jornalística
redator = Agent(
    name="Redator",
    model=OpenAIResponses(id="gpt-5-nano", api_key=os.getenv("OPENAI_API_KEY")),
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
    markdown=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# 4. DEFINIÇÃO DO WORKFLOW
#    O Workflow conecta os agentes em uma sequência lógica.
#    A saída de um agente serve de entrada para o próximo.
#    
#    pesquisa -> apuração -> verificação factual -> redação
# ─────────────────────────────────────────────────────────────────────────────
workflow = Workflow(
    name="Curador de Notícias com Workflow",
    description="Pesquisa, apura, verifica e redige matéria final",
    steps=[pesquisador, apurador, verificador, redator],
)


# ─────────────────────────────────────────────────────────────────────────────
# 5. EXECUÇÃO
#    Dispara o workflow com o tema inicial.
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    workflow.print_response("Novas tarifas dos EUA entram em vigor com taxa de 10%", stream=True, markdown=True)
