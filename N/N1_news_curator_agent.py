# =============================================================================
# N1 — Agente Curador de Notícias (Nível 1: agente único com Skills externas)
# =============================================================================
#
# Este script cria um ÚNICO AGENTE de IA que atua como jornalista completo.
# A diferença para o Nível 0 é que aqui as SKILLS (instruções de tarefas)
# são organizadas em ARQUIVOS EXTERNOS na pasta 'skills/', em vez de ficarem
# misturadas no código principal.
#
# TEMA → Pesquisa → Apuração → Verificação → Redação → Matéria Final (.md)
#
# Conceitos praticados neste nível:
#   • Modularização — separar instruções (prompt) do código Python
#   • Skills Loader — carregar habilidades dinamicamente de uma pasta
#   • Reutilização  — skills podem ser usadas por diferentes agentes
# =============================================================================


# ─────────────────────────────────────────────────────────────────────────────
# 1. IMPORTAÇÕES
#    Além das bibliotecas padrão e do framework Agno, importamos:
#    - Skills, LocalSkills → para carregar instruções de arquivos externos
# ─────────────────────────────────────────────────────────────────────────────
import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env (principalmente OPENAI_API_KEY)
load_dotenv()

from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from agno.skills import Skills, LocalSkills  # NOVO: Gerenciador de habilidades
from agno.tools.websearch import WebSearchTools
from agno.tools.file import FileTools


# ─────────────────────────────────────────────────────────────────────────────
# 2. CONFIGURAÇÃO DE DIRETÓRIOS E FERRAMENTAS
#    Definimos onde estao as skills e onde salvar os outputs.
# ─────────────────────────────────────────────────────────────────────────────

# Caminho para a pasta onde estão os arquivos de skills (.md ou .txt)
skills_dir = Path(__file__).parent / "skills"

# Caminho para a pasta onde a matéria final será salva
output_dir = Path(__file__).parent / "output/N1/"

# FileTools: permite ao agente manipular arquivos
file_tools = FileTools(
    base_dir=output_dir,          # diretório base para salvar arquivos
    enable_save_file=True,        # permite salvar (escrever) arquivos
    enable_read_file=True,        # permite ler arquivos
    enable_list_files=True,       # permite listar arquivos
)


# ─────────────────────────────────────────────────────────────────────────────
# 3. CRIAÇÃO DO AGENTE
#    Aqui montamos o agente. A grande novidade é o parâmetro 'skills'.
#
#    • skills=Skills(...) → Instruímos o agente a carregar habilidades
#                           da pasta 'skills_dir'.
#
#    Isso permite que o código Python fique limpo e focado na lógica,
#    enquanto os prompts complexos ficam em arquivos de texto separados.
# ─────────────────────────────────────────────────────────────────────────────
agente_noticias = Agent(
    name="Agente de Notícias",

    # Model: o cérebro do agente
    model=OpenAIResponses(id="gpt-5-nano", api_key=os.getenv("OPENAI_API_KEY")),

    # Skills: carrega habilidades da pasta local 'skills'
    # O agente vai ler os arquivos nessa pasta e entender como usar cada skill
    skills=Skills(loaders=[LocalSkills(str(skills_dir))]),

    # Instructions: Como usar as skills carregadas
    # Observe que agora referenciamos as skills pelos nomes dos arquivos/títulos
    instructions=[
        "Você é um jornalista completo: pesquisador, apurador, verificador factual e redator.",
        "Receba um tema e execute TODAS as etapas abaixo em sequência.",
        "",
        "Antes de começar, carregue as instruções de cada skill usando get_skill_instructions.",
        "",
        "ETAPA 1 — PESQUISA: use a skill 'pesquisa-noticias'",
        "ETAPA 2 — APURAÇÃO: use a skill 'apuracao-fontes'",
        "ETAPA 3 — VERIFICAÇÃO: use a skill 'verificacao-factual'",
        "ETAPA 4 — REDAÇÃO: use a skill 'redacao-jornalistica'",
        "",
        "Apresente ao usuário APENAS a matéria jornalística final (Etapa 4).",
        "As etapas 1, 2 e 3 são seu processo interno de trabalho.",
        "Salve o documento final em um arquivo .md no diretório",
    ],

    # Tools: ferramentas para pesquisa web e arquivos
    tools=[WebSearchTools(), file_tools],

    add_datetime_to_context=True,
    markdown=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# 4. EXECUÇÃO
#    Inicia o agente com um tema específico.
#    O parâmetro 'stream=True' faz a resposta aparecer palavra por palavra.
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    agente_noticias.print_response(
        "Novas tarifas dos EUA entram em vigor com taxa de 10%", 
        stream=True
    )