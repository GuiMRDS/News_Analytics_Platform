"""V5 — Investidor: notícias + dados de mercado para quem investe.

Research Team (mercado nacional + global) -> Apuração (loop) -> Validação de
Fontes -> Fact Checking (com dados de mercado) -> Análise de Mercado (cotações,
Selic, CDI, IPCA, dólar) -> Consolidação -> Redação -> Exportação Markdown

Otimizada para o limite de tokens por minuto do plano gratuito do Groq:
cada agente recebe o texto da sua skill direto nas instruções (sem a
requisição extra de get_skill_instructions) e tem limite de chamadas de
ferramenta ajustado ao papel.
"""

from agno.agent import Agent
from agno.team import Team
from agno.workflow import Workflow, Step, Loop
from agno.workflow.types import StepInput, StepOutput

from agente import passos
from agente.comum import (
    criar_busca,
    criar_modelo,
    diretorio_saida,
    ler_skill,
    verificar_api_key,
)
from agente.ferramentas_mercado import MercadoFinanceiroTools

VERSAO = "V5"
MIN_FONTES = 3
MAX_TENTATIVAS_APURACAO = 2

# Chamadas de ferramenta por agente (cada chamada = uma requisição ao LLM)
LIMITES = {
    "pesquisa": 2,
    "apuracao": 3,
    "verificacao": 2,
    "analise": 3,
}

output_dir = diretorio_saida(VERSAO)


def _agente(
    nome: str,
    skill: str,
    instrucoes: list[str],
    tools: list | None = None,
    limite: int | None = None,
    role: str | None = None,
) -> Agent:
    return Agent(
        name=nome,
        role=role,
        model=criar_modelo(),
        instructions=[
            *instrucoes,
            f"Siga as instruções da skill '{skill}' abaixo.",
            f"=== SKILL {skill} ===\n{ler_skill(skill)}",
        ],
        tools=tools or [],
        tool_call_limit=limite if tools else None,
        add_datetime_to_context=True,
        markdown=True,
    )


# ---------------------------------------------------------------------------
# Research Team
# ---------------------------------------------------------------------------

pesquisador_mercado_nacional = _agente(
    "Pesquisador de Mercado Nacional",
    "pesquisa-noticias",
    [
        "Você é um repórter de mercado financeiro brasileiro.",
        "Priorize Valor Econômico, InfoMoney, Bloomberg Línea, Estadão E-Investidor, Exame Invest, "
        "Money Times, B3, CVM e Banco Central. Pesquise em português.",
        "Inclua veículo e URL completa de cada notícia encontrada.",
    ],
    tools=[criar_busca()],
    limite=LIMITES["pesquisa"],
    role="Notícias de mercado no Brasil: B3, juros, inflação, câmbio, empresas, fundos e renda fixa.",
)

pesquisador_mercado_global = _agente(
    "Pesquisador de Mercado Global",
    "pesquisa-noticias",
    [
        "Você é um repórter de mercados globais.",
        "Priorize Reuters, Bloomberg, CNBC, Financial Times e Wall Street Journal. Pesquise em inglês.",
        "Destaque efeitos para o investidor brasileiro (dólar, commodities, juros americanos, BDRs).",
        "Inclua veículo e URL completa de cada notícia encontrada.",
    ],
    tools=[criar_busca()],
    limite=LIMITES["pesquisa"],
    role="Notícias de mercados globais: Fed, bolsas dos EUA, commodities, cripto e efeitos no Brasil.",
)

research_team = Team(
    name="Research Team de Mercado",
    model=criar_modelo(),
    members=[pesquisador_mercado_nacional, pesquisador_mercado_global],
    delegate_to_all_members=True,
    instructions=[
        "Você é o editor-chefe de uma redação de economia e investimentos.",
        "Delegue a pesquisa do tema a todos os membros e consolide os resultados.",
        "Temas fora do mercado financeiro também são aceitos: escolha a notícia mais relevante.",
        "Retorne exatamente: **Título**, **Resumo** (2-3 frases), **Fonte**, "
        "**Ativos e indicadores envolvidos** e **Palavras-chave**.",
        "Ao final, liste todas as fontes encontradas no formato: - **Nome do Veículo**: Título (URL).",
    ],
    add_datetime_to_context=True,
    markdown=True,
)


# ---------------------------------------------------------------------------
# Demais agentes
# ---------------------------------------------------------------------------

apurador = _agente(
    "Apurador de Fontes",
    "apuracao-fontes",
    [
        "Você é um apurador de fontes de jornalismo econômico.",
        "Receba a saída da equipe de pesquisa e monte o dossiê.",
        f"IMPORTANTE: Você DEVE ter no mínimo {MIN_FONTES} fontes distintas (aproveite as já listadas na entrada).",
        "Na seção '## FONTES COLETADAS', use SEMPRE: - **Nome do Veículo**: Título da matéria (URL)",
        "Se a apuração anterior não atingiu o mínimo, busque fontes DIFERENTES das já encontradas.",
    ],
    tools=[criar_busca()],
    limite=LIMITES["apuracao"],
)

verificador = _agente(
    "Verificador Factual",
    "verificacao-factual",
    [
        "Você é um verificador factual especializado em mercado financeiro.",
        "Receba o dossiê validado e verifique os fatos.",
        "Use as ferramentas de mercado para conferir cotações e indicadores citados no dossiê.",
        "Leve em conta a '## VALIDAÇÃO DE FONTES' no início do dossiê.",
        "Preserve veículos e URLs de todas as fontes na seção '## FONTES'.",
    ],
    tools=[criar_busca(), MercadoFinanceiroTools()],
    limite=LIMITES["verificacao"],
)

analista_mercado = _agente(
    "Analista de Investimentos",
    "analise-mercado",
    [
        "Você é um analista de investimentos que explica o mercado para pessoas físicas.",
        "Receba o relatório de verificação e produza a análise de mercado.",
        "Use somente dados retornados pelas ferramentas de mercado ou presentes no relatório.",
        "Nunca faça recomendação de compra ou venda.",
    ],
    tools=[MercadoFinanceiroTools()],
    limite=LIMITES["analise"],
)

redator = _agente(
    "Redator de Economia",
    "redacao-jornalistica",
    [
        "Você é um redator de jornalismo econômico profissional.",
        "Você receberá o RELATÓRIO DE VERIFICAÇÃO e a ANÁLISE DE MERCADO.",
        "Use a análise de mercado na seção '## O que isso significa para o investidor', citando dados com data e fonte.",
        f"Se o relatório indicar menos de {MIN_FONTES} fontes independentes, comece com: "
        "'⚠️ NOTA: Esta matéria foi produzida com um número limitado de fontes independentes.'",
        "Responda APENAS com a matéria em Markdown; o arquivo será salvo automaticamente.",
    ],
)


# ---------------------------------------------------------------------------
# Funções do workflow
# ---------------------------------------------------------------------------

fontes_suficientes = passos.criar_condicao_fontes(MIN_FONTES)


def validar_fontes(step_input: StepInput) -> StepOutput:
    return passos.validar_fontes(step_input, MIN_FONTES, MAX_TENTATIVAS_APURACAO)


def consolidar_para_redacao(step_input: StepInput) -> StepOutput:
    """Junta verificação + análise de mercado: o redator precisa das duas."""
    verificacao = step_input.get_step_content("verificacao") or ""
    analise = step_input.previous_step_content or ""
    return StepOutput(
        content=(
            "# RELATÓRIO DE VERIFICAÇÃO\n\n"
            f"{verificacao}\n\n"
            "# ANÁLISE DE MERCADO\n\n"
            f"{analise}"
        )
    )


def exportar_markdown(step_input: StepInput) -> StepOutput:
    return passos.exportar_markdown(step_input, output_dir)


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

pesquisa_step = passos.passo_agente(
    "pesquisa", research_team, "Research Team de mercado: Brasil + global"
)

apuracao_loop = Loop(
    name="apuracao_loop",
    description="Repete a apuração até atingir o mínimo de fontes",
    steps=[passos.passo_agente("apuracao", apurador, "Apuração multi-fonte")],
    max_iterations=MAX_TENTATIVAS_APURACAO,
    end_condition=fontes_suficientes,
)

investor_workflow = Workflow(
    name="Investidor: Notícias + Dados de Mercado",
    description=(
        "Research Team -> Apuração (loop) -> Validação -> Fact Check -> "
        "Análise de Mercado -> Redação -> Markdown"
    ),
    steps=[
        pesquisa_step,
        apuracao_loop,
        Step(name="validacao_fontes", description="Valida o mínimo de fontes", executor=validar_fontes),
        passos.passo_agente("verificacao", verificador, "Fact checking com dados de mercado"),
        passos.passo_agente("analise_mercado", analista_mercado, "Painel e impacto por classe de ativo"),
        Step(name="consolidacao", description="Verificação + análise para o redator", executor=consolidar_para_redacao),
        passos.passo_agente("redacao", redator, "Matéria para investidores"),
        Step(name="exportacao", description="Exporta a matéria para Markdown", executor=exportar_markdown),
    ],
)


if __name__ == "__main__":
    verificar_api_key()
    investor_workflow.print_response(
        "Como a decisão mais recente do Copom sobre a Selic afeta a renda fixa e a bolsa?",
        stream=True,
    )
