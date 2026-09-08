# =============================================================================
# N0 — Agente Curador de Notícias (Nível 0: agente único)
# =============================================================================
#
# Este script cria um ÚNICO AGENTE de IA que atua como jornalista completo.
# Ele recebe um tema e executa todo o pipeline sozinho:
#
#   TEMA → Pesquisa → Apuração → Verificação → Redação → Matéria Final (.md)
#
# Conceitos praticados neste nível:
#   • Agent   — o "trabalhador" de IA que recebe instruções e executa tarefas
#   • Model   — o LLM (modelo de linguagem) que o agente usa para "pensar"
#   • Tool    — ferramentas externas que o agente pode usar (ex: buscar na web)
#   • Skills  — habilidades definidas via prompt (instruções detalhadas)
# =============================================================================


# ─────────────────────────────────────────────────────────────────────────────
# 1. IMPORTAÇÕES
#    Carregamos as bibliotecas necessárias:
#    - os / Path     → para lidar com caminhos de arquivos e variáveis de ambiente
#    - dotenv        → para carregar a chave de API do arquivo .env
#    - agno          → framework de agentes de IA (Agent, Model, Tools)
# ─────────────────────────────────────────────────────────────────────────────
from pathlib import Path
import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env (principalmente OPENAI_API_KEY)
load_dotenv()

# Agent          → classe principal que representa um agente de IA
# OpenAIResponses → adaptador para usar modelos da OpenAI como cérebro do agente
# WebSearchTools → ferramenta que permite ao agente pesquisar na internet
# FileTools      → ferramenta que permite ao agente salvar/ler arquivos no disco
from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from agno.tools.websearch import WebSearchTools
from agno.tools.file import FileTools


# ─────────────────────────────────────────────────────────────────────────────
# 2. CONFIGURAÇÃO DE FERRAMENTAS (TOOLS)
#    Ferramentas são "superpoderes" que damos ao agente.
#    Sem elas, o agente só consegue conversar — não consegue acessar a internet
#    nem salvar arquivos.
#
#    Aqui configuramos o FileTools para:
#      • salvar a matéria final em arquivo .md
#      • ler arquivos existentes
#      • listar arquivos no diretório de saída
# ─────────────────────────────────────────────────────────────────────────────
output_dir = Path(__file__).parent / "output/N0/"

file_tools = FileTools(
    base_dir=output_dir,          # diretório onde os arquivos serão salvos
    enable_save_file=True,        # permite salvar arquivos
    enable_read_file=True,        # permite ler arquivos existentes
    enable_list_files=True,       # permite listar arquivos no diretório
)


# ─────────────────────────────────────────────────────────────────────────────
# 3. SKILLS (HABILIDADES) — DEFINIDAS VIA PROMPT
#    Skills são instruções detalhadas que ensinam o agente a executar tarefas
#    específicas. São injetadas no prompt do agente como texto.
#
#    Neste projeto, definimos 4 skills que formam o pipeline jornalístico:
#
#    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
#    │  PESQUISA    │ →  │  APURAÇÃO    │ →  │ VERIFICAÇÃO  │ →  │   REDAÇÃO    │
#    │ de Notícias  │    │  de Fontes   │    │   Factual    │    │  da Matéria  │
#    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
#
#    Cada skill define:
#      • Entrada esperada  — o que recebe
#      • Processo          — passos a seguir
#      • Formato de saída  — como deve entregar o resultado
#      • Regras            — restrições a obedecer
# ─────────────────────────────────────────────────────────────────────────────
instrucoes_prompt = """
# INSTRUÇÕES

## SKILL: PESQUISA DE NOTÍCIAS

Busque as notícias mais recentes sobre um tema e identifique a principal.

### Entrada esperada
- Tema de busca (ex: "política brasileira", "economia", "tecnologia")

### Processo
1. Busque as notícias **mais recentes** sobre o tema
2. Identifique a notícia principal (a mais relevante e atual)
3. Extraia palavras-chave para aprofundamento

### Formato de saída
Retorne exatamente:
1. **Título**: o título exato da notícia principal
2. **Resumo**: 2-3 frases do que aconteceu
3. **Fonte**: veículo onde encontrou
4. **Palavras-chave**: termos para buscar mais fontes sobre essa mesma notícia

### Regras
- Priorize notícias do dia atual
- Escolha a notícia com maior impacto e repercussão
- As palavras-chave devem ser específicas o suficiente para encontrar a mesma notícia em outros veículos

---

## SKILL: APURAÇÃO DE FONTES JORNALÍSTICAS

Workflow para investigar uma notícia em múltiplas fontes e produzir um dossiê estruturado de evidências.

### Quando usar
- Recebeu uma notícia e precisa verificar em outras fontes
- Precisa montar um dossiê de evidências sobre um assunto
- Quer cruzar informações de diferentes veículos

### Entrada esperada
- Título ou resumo da notícia a ser apurada
- Palavras-chave para busca (opcional — se não fornecidas, extraia do título)

### Processo
1. **Buscar fontes**: use as palavras-chave para buscar a mesma notícia em diferentes veículos (mínimo 3, ideal 5)
2. **Extrair fatos**: para cada fonte, registre dados, números, nomes e citações diretas
3. **Cruzar informações**: identifique consensos, contradições e exclusividades
4. **Montar dossiê**: produza o documento estruturado no formato abaixo

### Formato de saída
Produza o dossiê exatamente nesta estrutura:

```
## FONTES COLETADAS

Para cada fonte encontrada:
- **Veículo** | URL | Data/hora de publicação
- Fatos reportados (dados, números, nomes, citações diretas)
- Informação exclusiva dessa fonte (o que só ela traz)

## LINHA DO TEMPO

Eventos em ordem cronológica com a fonte entre colchetes.
Ex: "10h — Governo anuncia medida X [Folha] [Reuters]"

## PONTOS DE CONSENSO

Fatos que TODAS ou a maioria das fontes confirmam.

## CONTRADIÇÕES E DIVERGÊNCIAS

Dados que diferem entre fontes. Seja específico:
- Ex: "Folha diz R$ 2,5 bi; Estadão diz R$ 2,8 bi; Reuters diz USD 500 mi"
- Ex: "G1 afirma que a decisão foi unânime; Valor diz que houve 2 votos contrários"

## LACUNAS

O que nenhuma fonte esclareceu ou o que falta confirmar.
```

### Regras
- Mínimo de **3 fontes**, ideal **5 ou mais**
- Priorize veículos de credibilidade reconhecida (Reuters, AP, AFP, grandes jornais)
- Nunca invente dados — registre apenas o que as fontes efetivamente publicaram
- Seja específico nas contradições: cite valores, nomes e datas exatos de cada fonte
- Inclua a URL de cada fonte sempre que disponível

---

## SKILL: VERIFICAÇÃO FACTUAL

Análise crítica exaustiva de um dossiê de evidências jornalísticas.

### Entrada esperada
- Dossiê de evidências (produzido pela skill apuracao-fontes)

### Processo
Execute TODOS os passos em sequência, sem pedir permissão:

#### Passo 1 — Cruzamento inicial
Compare cada fato entre todas as fontes. Classifique como:
- **CONFIRMADO**: 2+ fontes concordam
- **DISPUTADO**: fontes divergem
- **NÃO VERIFICADO**: apenas 1 fonte

#### Passo 2 — Resolução de contradições
Para cada fato DISPUTADO:
1. Busque fonte oficial/primária (governo, nota oficial, Reuters/AP/AFP)
2. Busque dados brutos (relatórios, documentos, balanços)
3. Se encontrou nova informação, reavalie
4. Se persiste, busque com termos diferentes ou fontes internacionais
5. Após 3+ tentativas sem resolver → classifique como "não resolvida" com razão provável

#### Passo 3 — Preenchimento de lacunas
Para cada lacuna:
1. Busca específica sobre o ponto em aberto
2. Tente fontes alternativas (sites oficiais, agências internacionais)
3. Reformule a pesquisa com termos diferentes
4. Após 2+ tentativas → marque "pendente — esgotadas as fontes disponíveis"

#### Passo 4 — Verificação de fatos únicos
Para cada fato de fonte única:
1. Busque em pelo menos 2 fontes adicionais
2. Se confirmar → promova para CONFIRMADO
3. Se contradizer → mova para DISPUTADO e repita Passo 2
4. Se não encontrar → mantenha NÃO VERIFICADO com alerta

#### Passo 5 — Consistência final
Revise datas, nomes, valores e citações de todo o relatório.

### Formato de saída

```
## FATOS CONFIRMADOS
Fatos com alto grau de confiança + fontes que confirmam.

## FATOS DISPUTADOS RESOLVIDOS
Versão original das fontes → o que encontrou → veredito final.

## FATOS DISPUTADOS NÃO RESOLVIDOS
O que cada fonte diz, buscas feitas, razão provável, recomendação ao redator.

## FATOS NÃO VERIFICADOS
Informações de fonte única não corroboradas + buscas tentadas.

## LACUNAS RESOLVIDAS
Lacunas preenchidas + fonte usada.

## LACUNAS PENDENTES
O que permanece sem resposta + buscas tentadas.

## ALERTA AO REDATOR
- O que pode ser AFIRMADO com segurança
- O que DEVE ter ressalva (e qual)
- O que NÃO DEVE ser publicado sem confirmação adicional
- Nível de confiança geral (alto/médio/baixo)
```

### Regras
- Execute IMEDIATAMENTE, sem pedir permissão ou fazer perguntas
- Faça todas as buscas necessárias antes de classificar como "não resolvido"
- Explique a razão provável de cada contradição não resolvida
- Seja específico: cite valores, nomes e datas exatos

---

## SKILL: REDAÇÃO DE MATÉRIA JORNALÍSTICA

Escreva a notícia como se fosse publicada agora em um veículo de imprensa real.

### Entrada esperada
- Relatório de verificação factual (produzido pela skill verificacao-factual)

### Estrutura da matéria

#### Título
Crie um NOVO título jornalístico — não copie das fontes. Factual, forte e informativo.

Exemplos de bons títulos:
- "Governo federal anuncia corte de R$ 15 bi no Orçamento de 2026"
- "STF forma maioria e valida marco temporal para terras indígenas"
- "Dólar recua para R$ 5,12 após sinalização do Fed sobre juros"

#### Lide (1º parágrafo)
Responda: O QUÊ, QUEM, QUANDO, ONDE e POR QUÊ. Deve funcionar sozinho.

#### Corpo (3-5 parágrafos)
- Pirâmide invertida (fatos mais importantes primeiro)
- Atribuição natural: "Segundo o Ministério...", "De acordo com dados do IBGE..."
- Divergências de forma natural: "Enquanto a Folha aponta R$ 2,5 bi [1], o Estadão estima R$ 2,8 bi [2]"
- Fatos não verificados com ressalvas: "a informação ainda não foi confirmada oficialmente"
- Números, datas, nomes e dados concretos
- Citações diretas entre aspas quando disponíveis
- **CITAÇÕES OBRIGATÓRIAS**: Sempre que mencionar um dado, fato ou citação de uma fonte, insira a referência numérica correspondente entre colchetes — ex: [1], [2], [3]. Cada número deve corresponder a uma entrada na seção "Referências" no final do texto.

#### Contexto (1 parágrafo)
Cenário mais amplo, o que veio antes, por que importa.

#### Referências
No final da matéria, inclua uma seção `## Referências` com a lista numerada de TODAS as fontes citadas no texto, no formato:

```
## Referências

[1] Nome do Veículo — Título da matéria. URL
[2] Nome do Veículo — Título da matéria. URL
[3] Nome do Veículo — Título da matéria. URL
```

- Use a mesma numeração usada nas citações [1], [2] etc. no corpo do texto
- Inclua a URL completa de cada fonte (extraída do dossiê de apuração/verificação)
- Se o título exato não estiver disponível, use uma descrição breve do conteúdo
- TODAS as fontes mencionadas no corpo DEVEM aparecer na lista de referências
- TODAS as entradas na lista de referências DEVEM ser citadas pelo menos uma vez no corpo

### Regras inegociáveis
- Português brasileiro fluente, tom jornalístico profissional
- Sério, direto, imparcial — sem opinião, sem adjetivos desnecessários
- SEMPRE use citações numéricas [1], [2], [3] no corpo para indicar a fonte de cada informação
- SEMPRE inclua a seção "Referências" no final com URLs completas
- NUNCA use bullet points no corpo — escreva em PARÁGRAFOS corridos
- NUNCA invente dados, nomes ou citações
- Extensão: 400-600 palavras (sem contar a seção de referências)
- Deve parecer que saiu de uma redação de verdade, NÃO de uma IA
"""


# ─────────────────────────────────────────────────────────────────────────────
# 4. CRIAÇÃO DO AGENTE
#    Aqui montamos o agente juntando todas as peças:
#
#    • name         → nome de identificação do agente
#    • model        → o LLM que ele vai usar (cérebro)
#    • instructions → lista de instruções que definem o comportamento
#                     inclui as skills e a sequência de etapas do pipeline
#    • tools        → ferramentas disponíveis (busca web + manipulação de arquivos)
#    • add_datetime_to_context → injeta data/hora atual no contexto do agente
#    • markdown     → formata a saída em Markdown
#
#    O agente recebe as 4 skills via prompt e é instruído a executá-las
#    em sequência (Pesquisa → Apuração → Verificação → Redação),
#    apresentando ao usuário somente o resultado final (a matéria).
# ─────────────────────────────────────────────────────────────────────────────
agente_noticias = Agent(
    name="Agente de Notícias",

    # Model: qual LLM o agente usa para "pensar" e gerar texto
    model=OpenAIResponses(id="gpt-5-nano", api_key=os.getenv("OPENAI_API_KEY")),

    # Instructions: define o comportamento, a persona e o pipeline do agente
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

    # Tools: ferramentas que o agente pode invocar durante a execução
    # - WebSearchTools → permite buscar informações na internet
    # - file_tools     → permite salvar a matéria final em .md
    tools=[WebSearchTools(), file_tools],

    # Injeta data/hora atual no contexto (útil para priorizar notícias recentes)
    add_datetime_to_context=True,

    # Formata a resposta do agente em Markdown
    markdown=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# 5. EXECUÇÃO
#    Quando este arquivo é executado diretamente (python N0_news_curator_agent.py),
#    o agente recebe um tema e executa todo o pipeline:
#
#    1. Pesquisa a notícia principal sobre o tema
#    2. Apura em múltiplas fontes
#    3. Verifica os fatos cruzando as fontes
#    4. Redige a matéria jornalística final
#    5. Salva o resultado em arquivo .md
#
#    print_response() exibe a resposta em tempo real no terminal.
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    agente_noticias.print_response(
        "Novas tarifas dos EUA entram em vigor com taxa de 10%"
    )