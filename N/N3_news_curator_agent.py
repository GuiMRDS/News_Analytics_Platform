# =============================================================================
# N3 — Agente Curador de Notícias (Nível 3: Workflow com Team e Loops)
# =============================================================================
#
# Este script cria um WORKFLOW COMPLETO de IA que atua como uma redação jornalística.
# Ele recebe um tema e coordena diferentes agentes e equipes em etapas distintas:
#
#   TEMA → Pesquisa (Team) → Apuração (Loop) → Verificação → Redação → Matéria Final (.md)
#
# Conceitos praticados neste nível:
#   • Team      — uma equipe de agentes trabalhando juntos sob a coordenação de um líder
#   • Workflow  — orquestração do fluxo de trabalho dividindo o processo em etapas (Steps)
#   • Loop      — repetição de um Step até que uma condição específica (end condition) seja atingida
#   • Skills    — habilidades carregadas a partir de arquivos externos e compartilhadas
# =============================================================================


# ─────────────────────────────────────────────────────────────────────────────
# 1. IMPORTAÇÕES E CONFIGURAÇÕES INICIAIS
#    Carregamos as bibliotecas necessárias para o Workflow, Agents, Teams e Utils.
# ─────────────────────────────────────────────────────────────────────────────
import os
import re
from typing import List
from pathlib import Path
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env (principalmente OPENAI_API_KEY)
load_dotenv()

from agno.agent import Agent
from agno.team import Team
from agno.models.openai import OpenAIResponses
from agno.skills import Skills, LocalSkills
from agno.tools.websearch import WebSearchTools
from agno.tools.file import FileTools
from agno.workflow import Workflow, Step, Loop
from agno.workflow.types import StepOutput

# Constantes globais do pipeline
MIN_FONTES = 3
MAX_TENTATIVAS_APURACAO = 3

# ─────────────────────────────────────────────────────────────────────────────
# 2. CONFIGURAÇÃO DE SKILLS E FERRAMENTAS (TOOLS)
#    As skills agora são carregadas localmente de um diretório externo.
#    Também configuramos o FileTools para salvar e ler arquivos gerados.
# ─────────────────────────────────────────────────────────────────────────────
skills_dir = Path(__file__).parent / "skills"
shared_skills = Skills(loaders=[LocalSkills(str(skills_dir))])

output_dir = Path(__file__).parent / "output/N3/"
file_tools = FileTools(
    base_dir=output_dir,          # diretório onde os arquivos serão salvos
    enable_save_file=True,        # permite salvar arquivos
    enable_read_file=True,        # permite ler arquivos existentes
    enable_list_files=True,       # permite listar arquivos no diretório
)

# ─────────────────────────────────────────────────────────────────────────────
# 3. DEFINIÇÃO DOS AGENTES E EQUIPES
#    Neste nível, temos vários agentes especializados em papéis distintos.
#    Eles utilizam as shared_skills injetadas e seguem instruções específicas.
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

# Time de Pesquisa — a equipe lidera e coordena o pesquisador
time_research = Team(
    name="Research",
    model=OpenAIResponses(id="gpt-5-nano", api_key=os.getenv("OPENAI_API_KEY")),
    members=[pesquisador],
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

# 2) Apurador de Fontes — usa a skill de apuração multi-fonte
apurador = Agent(
    name="Apurador de Fontes",
    model=OpenAIResponses(id="gpt-5-nano", api_key=os.getenv("OPENAI_API_KEY")),
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
        f"Se o relatório indicar menos de {MIN_FONTES} fontes independentes, inclua um aviso claro no início da matéria: '⚠️ NOTA: Esta matéria foi produzida com um número limitado de fontes independentes.'",
        "IMPORTANTE: Ao citar qualquer dado, fato ou informação de uma fonte, insira a referência numérica [1], [2], [3] etc. no corpo do texto.",
        "IMPORTANTE: No final da matéria, inclua uma seção '## Referências' com a lista numerada de todas as fontes, incluindo nome do veículo, título e URL completa.",
        "OBRIGATÓRIO: Ao finalizar a redação, você DEVE salvar a matéria completa em um arquivo Markdown (.md) usando a ferramenta save_file.",
        "Use o nome de arquivo no formato: materia_<tema_resumido>_<data_YYYY-MM-DD>.md (ex: materia_economia_brasileira_2026-02-10.md).",
        "Nunca termine sem salvar o arquivo. Confirme o nome do arquivo salvo na sua resposta final.",
    ],
    tools=[file_tools],
    markdown=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# 4. FUNÇÕES AUXILIARES E CONDIÇÕES DE LOOP
#    Neste Nível 3, introduzimos o conceito de Loop, que permite que o fluxo
#    de trabalho (workflow) repita uma determinada etapa até que alcancemos
#    um critério de sucesso. Para fazer isso, precisamos de:
#    1. Uma métrica de avaliação (função contar_fontes) que diz se a resposta foi boa.
#    2. Uma condição de parada (função fontes_suficientes) que o Loop verifica
#       a cada iteração. Se a condição for atingida, o Loop é encerrado ou 
#       se alcançarmos o número de MAX_TENTATIVAS_APURACAO o loop finaliza.
# ─────────────────────────────────────────────────────────────────────────────

def contar_fontes(texto: str) -> int:
    """
    Função Auxiliar: Extração e contagem analítica
    
    Analisa o texto retornado pelo Agente Apurador para contar o número
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
    
    # Passo 1: Captura o conteúdo específico de FONTES COLETADAS através de Regex
    # `re.search`: procura a primeira ocorrência.
    # Padrão: Busca "## FONTES COLETADAS" (com espaços opcionais \s*), captura tudo (.*?)
    #         de forma preguiçosa até encontrar o próximo "##" ou final do texto (##|$).
    # `re.DOTALL`: Faz o `.` capturar também quebras de linha (\n).
    # `re.IGNORECASE`: Ignora maiúsculas/minúsculas.
    # `match.group(1)`: Pega apenas o conteúdo capturado, ignorando os títulos.
    match = re.search(
        r"##\s*FONTES COLETADAS(.*?)(##|$)", texto, re.DOTALL | re.IGNORECASE
    )
    if match:
        secao = match.group(1)

    # Passo 2: Busca listas formatadas padrão Markdown de fontes através de Regex
    # `re.findall`: encontra todas as ocorrências.
    # Padrão `r"^-\s+\*\*"`: Busca início de linha ^, hífen -, um ou mais espaços \s+ 
    #                        e dois asteriscos literais \*\* (indicando negrito no markdown).
    # `re.MULTILINE`: Trata cada nova linha como um novo início para o ^.
    fontes_por_marcador = re.findall(r"^-\s+\*\*", secao, re.MULTILINE)
    
    # Passo 3: Extrai e cria um agrupamento de valores únicos (set) das URLs 
    # encontradas no texto a fim de descartarmos rapidamente links repetidos.
    # Padrão `r"https?://[^\s\)]+"`: Busca links que começam com "http://" ou "https://", 
    #                               seguidos por 1 ou mais caracteres que NÃO sejam espaços
    #                               em branco nem parênteses de fechamento (comum no Markdown).
    # `set(...)`: Cria um conjunto para eliminar automaticamente as URLs duplicadas.
    urls = set(re.findall(r"https?://[^\s\)]+", secao))

    # Retornamos o número máximo capturado, pois alguns links podem não ter o marcador,
    # ou os marcadores não conter links. O maior balanço valida uma contagem sensata.
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
        # Se por algum motivo não houver saída do agente anterior, solicitamos nova iteração.
        return False
        
    # Extraímos a resposta obtida pela iteração mais recente do agente (índice [-1])
    latest = outputs[-1]
    
    # Extraímos o conteúdo em texto plano gerado por essa requisição do agente
    content = str(latest.content or "")
    
    # Por fim, passamos o texto final pela função analítica anterior que fará a
    # contagem. Comparamos o resultado usando a constante estática (MIN_FONTES) do topo.
    return contar_fontes(content) >= MIN_FONTES


# ─────────────────────────────────────────────────────────────────────────────
# 5. WORKFLOW STEPS (ETAPAS DO FLUXO)
#    Definição de cada passo individual que o workflow irá executar.
# ─────────────────────────────────────────────────────────────────────────────

# Step 1: Pesquisa usando o Team
pesquisa_step = Step(
    name="pesquisa",
    description="Pesquisa de notícias sobre o tema",
    team=time_research,
)

# Step 2 (Base): Apuração usando o Agente Apurador
apuracao_step = Step(
    name="apuracao",
    description="Apuração multi-fonte com verificação de fontes",
    agent=apurador,
)

# Step 2 (Loop): Repete a apuração_step até que 'fontes_suficientes' seja True ou
# atinja o número máximo de tentativas (MAX_TENTATIVAS_APURACAO).
apuracao_loop = Loop(
    name="apuracao_loop",
    description="Repete a apuração até atingir o mínimo de fontes",
    steps=[apuracao_step],
    max_iterations=MAX_TENTATIVAS_APURACAO,
    end_condition=fontes_suficientes,
)

# Step 3: Verificação Factual usando o Agente Verificador
verificacao_step = Step(
    name="verificacao",
    description="Verificação factual do dossiê",
    agent=verificador,
)

# Step 4: Redação usando o Agente Redator
redacao_step = Step(
    name="redacao",
    description="Redação jornalística final",
    agent=redator,
)

# ─────────────────────────────────────────────────────────────────────────────
# 6. CRIAÇÃO DO WORKFLOW
#    Orquestração de todas as etapas definidas acima em uma sequência linear.
# ─────────────────────────────────────────────────────────────────────────────

news_curator_workflow = Workflow(
    name="News Curator Pipeline",
    description="Pesquisa -> Apuração (loop) -> Verificação Factual -> Redação",
    steps=[pesquisa_step, apuracao_loop, verificacao_step, redacao_step],
)


# ─────────────────────────────────────────────────────────────────────────────
# 7. EXECUÇÃO
#    Inicializa o processo se o script for executado diretamente.
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    news_curator_workflow.print_response("Novas tarifas dos EUA entram em vigor com taxa de 10%", stream=True, markdown=True)
