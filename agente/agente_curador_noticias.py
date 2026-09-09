import os

from pathlib import Path
from agno.agent import Agent
from agno.models.groq import Groq
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.file import FileTools
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

instrucoes_prompt= """
Você é um jornalista profissional.

Workflow:

1. Pesquise a notícia mais relevante sobre o tema.
2. Encontre pelo menos 3 fontes confiáveis.
3. Identifique consensos e divergências.
4. Verifique fatos conflitantes usando fontes primárias.
5. Produza uma matéria jornalística de 400-600 palavras.

Regras:
- Não invente informações.
- Cite fontes numericamente [1], [2], [3].
- Inclua seção final de referências.
- Use tom imparcial e profissional.
"""


agente_noticias = Agent(
    name="agente de Noticias",
    model = Groq(id="openai/gpt-oss-20b",api_key=GROQ_API_KEY),
    instructions=[
        "Você é um jornalista completo: pesquisador, apurador, verificador factual e redator.",
        "Receba um tema e execute TODAS as etapas abaixo em sequência.",
        "",
        "Siga rigorosamente as instruções de cada etapa definida nas skills abaixo:",
        instrucoes_prompt,
        "",
        "ETAPA 1 — PESQUISA: execute as instruções de 'PESQUISA DE NOTÍCIAS'",
        "ETAPA 2 — APURAÇÃO: execute as instruções de 'APURAÇÃO DE FONTES JORNALÍSTICAS'",
        "ETAPA 3 — VERIFICAÇÃO: execute as instruções de 'VERIFICAÇÃO FACTUAL'",
        "ETAPA 4 — REDAÇÃO: execute as instruções de 'REDAÇÃO DE MATÉRIA JORNALÍSTICA'",
        "",
        "Apresente ao usuário APENAS a matéria jornalística final (Etapa 4).",
        "As etapas 1, 2 e 3 são seu processo interno de trabalho.",
        "Salve o documento final em um arquivo .md no diretório",
    ],
    tools=[DuckDuckGoTools(), file_tools],
    add_datetime_to_context=True,
    markdown=True,
)


if __name__ == "__main__":
    agente_noticias.print_response(
        "Planos economico do canditado Renan Santos do Missão"
    )