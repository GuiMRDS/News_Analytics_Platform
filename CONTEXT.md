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
| Linguagem | Python **3.12–3.13** (`>=3.12,<3.14`; `.python-version` = 3.13). Somente Python **do sistema** (`[tool.uv] python-preference = "only-system"`), ver §9 |
| Gerenciador de pacotes | `uv` (`uv.lock` versionado) |
| Framework de agentes | `agno==2.4.8` (`Agent`, `Team`, `Workflow`, `Step`, `Loop`, `Skills`, `LocalSkills`) |
| LLM | Groq, modelo `openai/gpt-oss-20b` |
| Busca | `DuckDuckGoTools` do Agno (`ddgs`, `duckduckgo-search`) |
| Persistência | Arquivos Markdown em `output/<versão>/` |
| Interface | Streamlit (chat) |
| Testes | `pytest` + `streamlit.testing.v1.AppTest`; CI no GitHub Actions |
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
│   ├── registry.py             # VERSOES + carregar_workflow (import sob demanda)
│   └── components/sidebar.py   # Detalhes da versão + botão "Nova conversa"
├── tests/                      # pytest (sem LLM): comum, skills, versões, UI
├── .github/workflows/testes.yml  # CI: pytest em Ubuntu/Windows × Python 3.12/3.13
├── output/                     # gerado em runtime (ignorado pelo git)
├── .env.example
├── .python-version             # 3.13
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

## 7. Interface Streamlit (chat)

- `ui/app.py`: interface de **chat** (`st.chat_input` / `st.chat_message`). Um `st.segmented_control` (key `versao`) acima da conversa permite **trocar a versão dos agentes a qualquer momento**; cada resposta mostra a versão que a gerou. O histórico fica em `st.session_state.mensagens` (`{"papel", "conteudo", "versao"}`). Erros do workflow aparecem como mensagem no chat, sem derrubar a página. Sem `GROQ_API_KEY`, mostra erro e para.
- `ui/app.py` insere a raiz e `ui/` no `sys.path` **antes** de importar `registry`/`agente`.
- `ui/registry.py`: `VERSOES` (chave `V1`..`V4` → `Versao(rotulo, modulo, objeto, descricao, pipeline)`), `VERSAO_PADRAO = "V4"` e `carregar_workflow(chave)`, que importa a versão **sob demanda** com cache (`lru_cache`). Abrir a UI não instancia todas as versões.
- `ui/components/sidebar.py`: descrição/pipeline da versão ativa e botão "Nova conversa" (key `nova_conversa`).
- Todas as versões expõem `.run()` / `.print_response()` e são intercambiáveis.

---

## 8. Execução e testes

```bash
uv sync
cp .env.example .env                        # e preencha GROQ_API_KEY
uv run python -m agente.agente_curador_v4   # roda o exemplo "Quem é Gustavo Guanabara?"
uv run python -m streamlit run ui/app.py
uv run python -m pytest                     # 36 testes, sem LLM, ~3 s
```

- As versões devem ser executadas **como módulo** (`python -m agente.<arquivo>`) a partir da raiz, porque importam `agente.comum`.
- Testes: `tests/conftest.py` define `GROQ_API_KEY` fictícia; `test_comum.py` (contagem de fontes, chave, caminhos), `test_skills.py` (frontmatter e contrato `## FONTES COLETADAS`), `test_versoes.py` (estrutura dos workflows V3/V4, loop, validação, slug, exportação, skills citadas existem), `test_ui.py` (AppTest com workflows falsos: chat, troca de versão, erro, nova conversa, chave ausente).
- CI: `.github/workflows/testes.yml` roda `uv sync --locked` + `pytest` em push para `main`, PRs e manualmente.

## 9. Windows e Smart App Control

A máquina de desenvolvimento (Windows 11 Home) tem o **Smart App Control ativado**, que bloqueia binários sem assinatura digital:
- o Python baixado pelo uv (python-build-standalone): `ImportError: DLL load failed while importing unicodedata/_socket: Uma política de Controle de Aplicativo bloqueou este arquivo`;
- os executáveis gerados em `.venv\Scripts` (ex.: `streamlit.exe`): `os error 4551`.

Solução adotada: usar o **Python oficial** (assinado pela PSF; instalado com `py install 3.13`), forçar o uv a usá-lo com `python-preference = "only-system"` e executar ferramentas sempre via **`python -m <ferramenta>`**. Se o `.venv` tiver sido criado com o Python do uv, apague-o e rode `uv sync` de novo.

---

## 10. Pontos em aberto

1. **Nenhuma versão foi executada ponta a ponta com o LLM** após a refatoração (os testes cobrem estrutura e lógica determinística). Validar a orquestração do `Team` e do `Loop` da V4 em uma execução real.
2. Os testes não avaliam a **qualidade** das matérias; uma suíte opcional de avaliação com LLM (marcada e fora do CI) seria o próximo passo.
3. Definições de agentes continuam repetidas entre versões — intencional, para que cada versão permaneça autocontida e comparável.
4. Histórico git com várias mensagens de commit genéricas (`#`).
