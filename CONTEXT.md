# CONTEXT.md — News Analytics Platform (Curadoria de Notícias com IA)

Documento de contexto do projeto: o que é, como está organizado, como funciona e quais são as lacunas conhecidas. Para regras de trabalho de agentes de código, veja [AGENTS.md](AGENTS.md).

---

## 1. Visão geral

Sistema de curadoria jornalística baseado em agentes de IA. Recebe um **tema** e produz uma **matéria jornalística em Markdown**, simulando o fluxo de uma redação: pesquisa → apuração → verificação factual → redação.

O projeto é também um laboratório de **engenharia de agentes**: cada versão (V1 a V4) explora uma arquitetura de orquestração diferente com o framework **Agno**, permitindo comparar as abordagens.

- **Autor:** Guilherme Marinho ([GitHub](https://github.com/GuiMRDS))
- **Repositório:** `https://github.com/GuiMRDS/News_Analytics_Platform`
- **Nome do pacote (`pyproject.toml`):** `news-curator` v0.1.0
- **Idioma do domínio:** português brasileiro (prompts, skills, saída e nomes de variáveis)

---

## 2. Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python **3.12.11** (fixado em `pyproject.toml`) |
| Gerenciador de pacotes | `uv` (`uv.lock` versionado) |
| Framework de agentes | `agno==2.4.8` (`Agent`, `Team`, `Workflow`, `Step`, `Loop`, `Skills`, `LocalSkills`) |
| LLM | Groq, modelo `openai/gpt-oss-20b` |
| Busca | `DuckDuckGoTools` do Agno (`ddgs`, `duckduckgo-search`) |
| Persistência | Arquivos Markdown em `output/<versão>/` |
| Interface | Streamlit |
| Configuração | `.env` na raiz com `GROQ_API_KEY` (modelo em `.env.example`), carregado via `python-dotenv` |

---

## 3. Estrutura do repositório

```text
News_Analytics_Platform/
├── agente/                     # pacote Python
│   ├── __init__.py
│   ├── comum.py                # caminhos, modelo Groq, skills, FileTools, contar_fontes
│   ├── agente_curador.py       # V1: agente monolítico (exporta `agente_noticias`)
│   ├── agente_curador_v2.py    # V2: workflow sequencial (exporta `workflow`)
│   ├── agente_curador_v3.py    # V3: Step + Loop (exporta `news_curator_workflow`)
│   └── agente_curador_v4.py    # V4: Team + Loop + validação + exportação (exporta `research_pipeline_workflow`)
├── skills/                     # Skills Agno (SKILL.md com frontmatter YAML)
│   ├── pesquisa-noticias/
│   ├── apuracao-fontes/
│   ├── verificacao-factual/
│   └── redacao-jornalistica/
├── ui/
│   ├── app.py                  # App Streamlit
│   ├── registry.py             # Mapa "nome da versão" -> agente/workflow
│   └── components/sidebar.py   # Seletor de versão
├── output/                     # gerado em runtime (ignorado pelo git)
├── .env.example
├── pyproject.toml / uv.lock
└── README.md
```

---

## 4. Módulo compartilhado (`agente/comum.py`)

| Símbolo | Descrição |
|---|---|
| `BASE_DIR`, `SKILLS_DIR`, `OUTPUT_DIR` | Caminhos resolvidos a partir da raiz do repositório |
| `MODELO_ID` | `"openai/gpt-oss-20b"` |
| `obter_api_key()` / `verificar_api_key()` | Lê a `GROQ_API_KEY`; a segunda levanta `RuntimeError` com mensagem clara se faltar |
| `criar_modelo()` | Instância `Groq` configurada |
| `carregar_skills()` | `Skills(LocalSkills(SKILLS_DIR))`; falha se a pasta não existir |
| `diretorio_saida(versao)` / `criar_file_tools(versao)` | Cria `output/<versao>` e o `FileTools` correspondente |
| `contar_fontes(texto)` | Conta fontes distintas na seção `## FONTES COLETADAS`: `max(veículos únicos em **negrito**, URLs únicas)` |

`load_dotenv` é chamado no import de `comum`. Importar qualquer versão instancia os agentes e cria o diretório de saída (efeito colateral no import, usado pela UI).

---

## 5. Pipeline jornalístico (domínio)

Cada etapa é uma **skill** em `skills/<nome>/SKILL.md`. Os agentes carregam as instruções em tempo de execução via `get_skill_instructions`. A saída de uma etapa é a entrada da seguinte.

| # | Skill | Papel | Entrada | Saída (seções) |
|---|---|---|---|---|
| 1 | `pesquisa-noticias` | Pesquisador | Tema | Título, Resumo, Fonte, Palavras-chave |
| 2 | `apuracao-fontes` | Apurador | Notícia + palavras-chave | `## FONTES COLETADAS`, `## LINHA DO TEMPO`, `## PONTOS DE CONSENSO`, `## CONTRADIÇÕES E DIVERGÊNCIAS`, `## LACUNAS` |
| 3 | `verificacao-factual` | Verificador | Dossiê | Fatos confirmados / disputados (resolvidos e não) / não verificados, lacunas, `## ALERTA AO REDATOR` |
| 4 | `redacao-jornalistica` | Redator | Relatório de verificação | Matéria de 400–600 palavras + `## Referências` |

### Regras editoriais centrais
- **Nunca inventar** dados, nomes ou citações.
- Mínimo de **3 fontes** (ideal 5+), priorizando Reuters, AP, AFP e grandes jornais.
- Classificação de fatos: **CONFIRMADO** (2+ fontes), **DISPUTADO** (divergência), **NÃO VERIFICADO** (1 fonte).
- Matéria: título original, lide (o quê/quem/quando/onde/por quê), pirâmide invertida, parágrafo de contexto, **sem bullet points no corpo**, tom imparcial.
- Citações numéricas `[1]`, `[2]`… no corpo, todas correspondendo à seção `## Referências` (veículo — título. URL) e vice-versa.

---

## 6. Versões da arquitetura

### V1 — Agente monolítico (`agente_curador.py`)
Um único `Agent` executa as 4 skills em sequência e mostra só a matéria final. Ferramentas: DuckDuckGo + FileTools. Saída: `output/V1`.

### V2 — Workflow sequencial (`agente_curador_v2.py`)
Quatro agentes (`pesquisador`, `apurador`, `verificador`, `redator`) passados diretamente como `steps` de um `Workflow`. Cada agente salva seu resultado em arquivo. Saída: `output/V2`.

### V3 — Workflow com controle de qualidade (`agente_curador_v3.py`)
```text
pesquisa_step → apuracao_loop[apuracao_step] → verificacao_step → redacao_step
```
- `MIN_FONTES = 3`, `MAX_TENTATIVAS_APURACAO = 3`.
- `Loop` repete a apuração até `fontes_suficientes(outputs)` ser `True` ou atingir o máximo de iterações.
- O apurador é instruído a usar `- **Nome do Veículo**: Título (URL)` — essencial para `contar_fontes` funcionar.
- O redator adiciona aviso `⚠️ NOTA` se houver menos de `MIN_FONTES` fontes e salva `materia_<tema>_<YYYY-MM-DD>.md` via `save_file`. Saída: `output/V3`.

### V4 — Multi-Agent Research Pipeline (`agente_curador_v4.py`) — versão atual
```text
pesquisa_step (Research Team)
  → apuracao_loop[apuracao]
  → validacao_fontes   (função, sem LLM)
  → verificacao
  → redacao
  → exportacao         (função, sem LLM)
```
- **Research Team** (`agno.team.Team`, `delegate_to_all_members=True`): `Pesquisador Nacional` (veículos brasileiros, PT) e `Pesquisador Internacional` (agências/veículos internacionais, EN+PT). O líder consolida a notícia principal no formato da skill `pesquisa-noticias` e lista todas as fontes.
- **Loop de apuração** igual à V3.
- **`validar_fontes`**: conta fontes de forma determinística e prefixa o dossiê com `## VALIDAÇÃO DE FONTES` (✅ aprovado ou ⚠️ insuficiente), sinalizando ao verificador e ao redator.
- **`exportar_markdown`**: salva a matéria em `output/V4/materia_<slug-do-tema>_<YYYY-MM-DD>.md` sem depender de o LLM chamar a ferramenta, e anexa o caminho do arquivo à resposta. Nesta versão os agentes não usam `FileTools`.

---

## 7. Interface Streamlit

- `ui/app.py` insere a raiz do repositório no `sys.path` **antes** de importar `registry`/`agente`, mostra erro e para se a `GROQ_API_KEY` não estiver configurada, lê o tema, chama `workflow.run(tema)` e exibe `resultado.content`.
- `ui/registry.py` monta `WORKFLOWS` (V4 primeiro, como padrão; depois V3, V2, V1).
- `ui/components/sidebar.py` renderiza o `selectbox` com as versões.
- Todas as versões expõem `.run()` / `.print_response()` e são intercambiáveis.

---

## 8. Execução

```bash
uv sync
cp .env.example .env                       # e preencha GROQ_API_KEY
uv run python -m agente.agente_curador_v4  # roda o exemplo "Quem é Gustavo Guanabara?"
uv run streamlit run ui/app.py
```

As versões devem ser executadas **como módulo** (`python -m agente.<arquivo>`) a partir da raiz, porque importam `agente.comum`.

---

## 9. Pontos em aberto

1. **Sem testes automatizados nem CI.** Bons candidatos: `contar_fontes`, `validar_fontes`, `_slug`, `exportar_markdown` (lógica pura, sem LLM).
2. **V4 não foi executada ponta a ponta** após a criação (apenas compilada): o Python instalado pelo uv estava bloqueado pela política de Controle de Aplicativo do Windows (`_socket` DLL). Validar a orquestração do `Team` e do `Loop` em uma execução real.
3. Definições de agentes continuam repetidas entre versões — intencional, para que cada versão permaneça autocontida e comparável.
4. Histórico git com várias mensagens de commit genéricas (`#`).
