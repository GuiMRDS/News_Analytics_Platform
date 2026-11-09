from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools

from agente.comum import (
    carregar_skills,
    criar_file_tools,
    criar_modelo,
    verificar_api_key,
)

file_tools = criar_file_tools("V1")

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
    model=criar_modelo(),
    skills=carregar_skills(),
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
        "Salve o documento final em um arquivo .md usando a ferramenta save_file.",
    ],
    tools=[DuckDuckGoTools(), file_tools],
    add_datetime_to_context=True,
    markdown=True,
)


if __name__ == "__main__":
    verificar_api_key()
    agente_noticias.print_response(
        "Quem é Gustavo Guanabara?",
        stream=True
    )