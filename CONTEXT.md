# CONTEXT.md — News Analytics Platform (Curadoria de Notícias com IA)

Documento de contexto do projeto: o que é, como está organizado, como funciona hoje e quais são as lacunas conhecidas. Para regras de trabalho de agentes de código, veja [AGENTS.md](AGENTS.md).

---

## 1. Visão geral

Sistema de curadoria jornalística baseado em agentes de IA. Recebe um **tema** e produz uma **matéria jornalística em Markdown**, simulando o fluxo de uma redação: pesquisa → apuração → verificação factual → redação.

O projeto é também um laboratório de **engenharia de agentes**: cada versão (V1, V2, V3, V4 planejada) explora uma arquitetura de orquestração diferente com o framework **Agno**, permitindo comparar as abordagens.

- **Autor:** Guilherme Marinho ([GitHub](https://github.com/GuiMRDS))
- **Repositório:** `https://github.com/GuiMRDS/News_Analytics_Platform` (o README ainda cita o nome antigo `Curadoria_Noticias`)
- **Nome do pacote (`pyproject.toml`):** `news-curator` v0.1.0
- **Idioma do domínio:** português brasileiro (prompts, skills, saída e nomes de variáveis)

---

## 2. Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python **3.12.11** (fixado em `pyproject.toml`; o README diz 3.13+, o que está desatualizado) |
| Gerenciador de pacotes | `uv` (`uv.lock` versionado) |
| Framework de agentes | `agno==2.4.8` (`Agent`, `Workflow`, `Step`, `Loop`, `Skills`, `LocalSkills`) |
| LLM | Groq, modelo `openai/gpt-oss-20b` |
| Busca | `DuckDuckGoTools` do Agno (`ddgs`, `duckduckgo-search`) |
| Persistência | Arquivos Markdown via `FileTools` do Agno |
| Interface | Streamlit |
| Configuração | `.env` com `GROQ_API_KEY` (carregado com `python-dotenv`, que vem como dependência transitiva do Agno) |

Também declaradas, mas **sem uso no código atual**: `fastapi`, `openai`, `newspaper3k`, `sqlalchemy`, `sc-pylibs`.

---

## 3. Estrutura do repositório

```text
News_Analytics_Platform/
├── agente/
│   ├── agente_curador.py      # V1: agente monolítico (exporta `agente_noticias`)
│   ├── agente_curador_v2.py   # V2: workflow sequencial (exporta `workflow`)
│   └── agente_curador_v3.py   # V3: workflow com Step + Loop (exporta `news_curator_workflow`)
├── skills/                    # Skills Agno (SKILL.md com frontmatter YAML)
│   ├── pesquisa-noticias/
│   ├── apuracao-fontes/
│   ├── verificacao-factual/
│   └── redacao-jornalistica/
├── ui/
│   ├── app.py                 # App Streamlit
│   ├── registry.py            # Mapa "nome da versão" -> agente/workflow
│   └── components/sidebar.py  # Seletor de versão
├── pyproject.toml / uv.lock
├── README.md
└── .gitignore                 # ignora .env, .venv/, output/, __pycache__/, *.log
```

Não há testes, CI, `requirements.txt` nem `.env.example`.

---

## 4. Pipeline jornalístico (domínio)

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

## 5. Versões da arquitetura

### V1 — Agente monolítico (`agente/agente_curador.py`)
Um único `Agent` ("agente de Noticias") executa as 4 skills em sequência e mostra só a matéria final. Ferramentas: DuckDuckGo + FileTools. Saída: `agente/output/V0`.

### V2 — Workflow sequencial (`agente/agente_curador_v2.py`)
Quatro agentes (`pesquisador`, `apurador`, `verificador`, `redator`) passados diretamente como `steps` de um `Workflow`. Cada agente salva seu resultado em arquivo. O redator não tem busca, só FileTools. Saída: `agente/output/V2`.

### V3 — Workflow com controle de qualidade (`agente/agente_curador_v3.py`) — versão mais recente implementada
```text
pesquisa_step → apuracao_loop[apuracao_step] → verificacao_step → redacao_step
```
- `MIN_FONTES = 3`, `MAX_TENTATIVAS_APURACAO = 3`.
- `Loop` repete a apuração até `fontes_suficientes(outputs)` retornar `True` ou atingir o máximo de iterações.
- `contar_fontes(texto)`: isola a seção `## FONTES COLETADAS` (se existir) e retorna `max(veículos únicos em **negrito**, URLs únicas)`.
- O apurador é instruído a usar o formato `- **Nome do Veículo**: Título (URL)` — essencial para a contagem funcionar.
- O redator adiciona aviso `⚠️ NOTA` se houver menos de `MIN_FONTES` fontes e deve salvar `materia_<tema_resumido>_<YYYY-MM-DD>.md`.
- Um agente `time_research` ("líder da equipe de pesquisa") está definido mas **não é usado** no workflow — embrião da Research Team da V4.

### V4 — Multi-Agent Research Pipeline (planejada, não existe no código)
O README descreve uma V4 (`agente/agente_curador_v4.py`) com **Research Team** (`agno.team.Team`), loop de apuração, validação de fontes, fact checking e exportação Markdown. O arquivo ainda não foi criado e não está registrado na UI.

---

## 6. Interface Streamlit

- `ui/registry.py` importa os objetos de cada versão e monta `WORKFLOWS = {"V1 - Agent Único": ..., "V2 - Workflow": ..., "V3 - Loop + Fact Check": ...}`.
- `ui/components/sidebar.py` renderiza um `selectbox` com as chaves do registro.
- `ui/app.py` lê o tema, chama `workflow.run(tema)` e exibe `resultado.content` em Markdown.
- Todas as versões expõem a mesma interface (`.run()` / `.print_response()`), o que permite tratá-las de forma intercambiável.

---

## 7. Execução

```bash
uv sync
# criar .env com GROQ_API_KEY=...
python agente/agente_curador_v3.py   # roda o exemplo "Quem é Gustavo Guanabara?"
streamlit run ui/app.py
```

Note que importar qualquer módulo `agente/*` já instancia agentes e cria diretórios de saída (efeito colateral no import).

---

## 8. Problemas conhecidos / dívida técnica

1. **Caminho das skills em V1 e V2:** usam `Path(__file__).parent / "skills"` → `agente/skills`, que não existe. A V3 usa corretamente `BASE_DIR / "skills"` (raiz do repo) e falha cedo se não existir.
2. **Diretório de saída da V3** aponta para `output/V2` (copiado da V2); deveria ser `output/V3`. As saídas ficam em `agente/output/...`, não em `output/` na raiz como o README sugere (ambos ignorados pelo git).
3. **Import da UI:** `ui/app.py` faz `from registry import WORKFLOWS` (que importa `agente.*`) **antes** de inserir a raiz do repo no `sys.path`, então o import de `agente` pode falhar dependendo de como o Streamlit é iniciado.
4. **V4 documentada mas inexistente**; `time_research` definido e não utilizado.
5. **README desatualizado:** Python 3.13+ (real: 3.12.11), `pip install -r requirements.txt` (arquivo não existe), nome do repositório antigo.
6. **Código duplicado:** modelo Groq, `FileTools` e definições de agentes repetidos em cada versão.
7. **Dependências não usadas** no `pyproject.toml` e `description` padrão ("Add your description here").
8. Sem testes automatizados, sem `.env.example`, sem tratamento de `GROQ_API_KEY` ausente.
9. Histórico git com várias mensagens de commit genéricas (`#`).
