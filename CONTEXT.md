# CONTEXT.md — News Analytics Platform (Notícias e Inteligência para Investidores)

Documento de contexto do projeto: o que é, como está organizado, como funciona e quais são as lacunas conhecidas. Para regras de trabalho de agentes de código, veja [AGENTS.md](AGENTS.md).

---

## 1. Visão geral

Plataforma de notícias **especializada em mercado financeiro e investimentos**: ações, renda fixa, renda variável, fundos (incluindo FIIs), câmbio, cripto, juros, inflação e economia. O objetivo é ajudar investidores a entender notícias e cotações. Temas fora do mercado também são aceitos.

Uma "redação" de agentes de IA (**Agno** + **Groq**) recebe uma pergunta ou tema, pesquisa, apura em múltiplas fontes, checa fatos, cruza com **dados reais de mercado** (Yahoo Finance e Banco Central) e entrega uma matéria em Markdown com a seção "O que isso significa para o investidor". Nunca faz recomendação de investimento.

O projeto também é um laboratório de **engenharia de agentes**: cada versão (V1 a V5) usa uma arquitetura diferente, e todas podem ser comparadas pela UI.

- **Autor:** Guilherme Marinho ([GitHub](https://github.com/GuiMRDS))
- **Repositório:** `https://github.com/GuiMRDS/News_Analytics_Platform`
- **Pacote (`pyproject.toml`):** `news-curator` v0.1.0
- **Idioma do domínio:** português brasileiro

---

## 2. Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python **3.12–3.13** (`>=3.12,<3.14`; `.python-version` = 3.13). Somente Python **do sistema** (`[tool.uv] python-preference = "only-system"`), ver §10 |
| Pacotes | `uv` (`uv.lock` versionado) |
| Agentes | `agno==2.4.8` (`Agent`, `Team`, `Workflow`, `Step`, `Loop`) |
| LLM | Groq, `openai/gpt-oss-20b` por padrão (`GROQ_MODEL_ID`) |
| Busca | `WebSearchTools` do Agno sobre `ddgs`, backend `auto` (`BUSCA_BACKEND`) |
| Dados de mercado | `yfinance` (B3 com sufixo `.SA`, EUA, índices, câmbio, cripto, commodities) + API SGS do Banco Central |
| Interface | Streamlit (chat + painel de mercado) |
| Testes | `pytest` + `streamlit.testing.v1.AppTest`; CI no GitHub Actions |
| Configuração | `.env` (`GROQ_API_KEY`; opcionais `GROQ_MODEL_ID`, `BUSCA_BACKEND`), modelo em `.env.example` |

`fastapi` é obrigatório: `agno.workflow` o importa.

---

## 3. Estrutura do repositório

```text
News_Analytics_Platform/
├── agente/
│   ├── comum.py                 # modelo, busca, skills, caminhos, contar_fontes, ler_skill, erros amigáveis
│   ├── passos.py                # passo_agente, validar_fontes, exportar_markdown, slug, condição do loop
│   ├── ferramentas_mercado.py   # MercadoFinanceiroTools + funções de cotação/indicadores/simulação
│   ├── agente_curador.py        # V1 (agente_noticias)
│   ├── agente_curador_v2.py     # V2 (workflow)
│   ├── agente_curador_v3.py     # V3 (news_curator_workflow)
│   ├── agente_curador_v4.py     # V4 (research_pipeline_workflow)
│   └── agente_curador_v5.py     # V5 — Investidor (investor_workflow)
├── skills/                      # SKILL.md com frontmatter YAML
│   ├── pesquisa-noticias/  apuracao-fontes/  verificacao-factual/
│   ├── analise-mercado/    redacao-jornalistica/
├── ui/
│   ├── app.py                   # chat + seletor de versão + sugestões
│   ├── registry.py              # VERSOES, VERSAO_PADRAO="V5", carregar_workflow (lazy)
│   └── components/sidebar.py    # painel de mercado + detalhes da versão + nova conversa
├── tests/                       # conftest (mercado simulado), comum, passos, ferramentas, skills, versões, UI
├── .github/workflows/testes.yml # CI: Ubuntu/Windows × Python 3.12/3.13
├── output/                      # matérias geradas (ignorado pelo git)
└── .env.example / .python-version / pyproject.toml / uv.lock
```

---

## 4. Módulos compartilhados

### `agente/comum.py`
- Caminhos: `BASE_DIR`, `SKILLS_DIR`, `OUTPUT_DIR`. `load_dotenv` roda no import.
- `criar_modelo()`: Groq com `GROQ_MODEL_ID` e `max_retries=TENTATIVAS_API` (5); o SDK respeita o `retry-after` em erros 429.
- `criar_busca()`: `WebSearchTools(backend="auto", fixed_max_results=MAX_RESULTADOS_BUSCA)` (5). **Não use `DuckDuckGoTools`**: ele fixa o backend `duckduckgo`, que parou de retornar resultados.
- `LIMITE_CHAMADAS_FERRAMENTAS` (4): `tool_call_limit` padrão da V4.
- `carregar_skills()`, `ler_skill(nome)` (corpo do SKILL.md sem o frontmatter), `diretorio_saida`, `criar_file_tools`, `contar_fontes`, `verificar_api_key`, `mensagem_erro_amigavel` (traduz 413/429/401 do Groq).

### `agente/passos.py`
- `passo_agente(nome, agente_ou_team, descricao, max_retries=1)`: um `Step` com executor que roda o agente **sem streaming** e verifica `RunStatus.error`. Se falhar, levanta `ErroDoAgente` com a causa real. **Por quê:** no Agno 2.4.8, quando um agente falha dentro de `Step(agent=...)`, o erro real (ex.: 413 do Groq) é escondido por `'NoneType' object has no attribute 'parent_run_id'`. V2 a V5 usam esse wrapper.
- `criar_condicao_fontes(min)`, `validar_fontes(step_input, min, tentativas)`, `slug`, `exportar_markdown(step_input, pasta)`.

### `agente/ferramentas_mercado.py`
- Funções puras: `normalizar_ticker` (`petr4` → `PETR4.SA`; apelidos como IBOV, DOLAR, BITCOIN, BRENT), `aliquota_ir` (tabela regressiva de 22,5% a 15%), `simular_renda_fixa`, `resumir_historico`.
- Acesso a dados, isolado para os testes: `_historico(ticker, periodo)` (yfinance) e `_buscar_serie_bcb(codigo)` (SGS: 432 Selic meta, 4389 CDI, 13522 IPCA 12m, 1 PTAX).
- Alto nível: `obter_cotacao`, `obter_indicadores`, `obter_panorama`. Nunca levantam exceção; em caso de falha devolvem `{"erro": ...}`.
- `MercadoFinanceiroTools` (Toolkit): `cotacao_ativo`, `indicadores_economicos`, `panorama_mercado`, `simular_investimento_renda_fixa`, todas retornando JSON compacto.

---

## 5. Pipeline e skills (domínio)

| Skill | Papel | Saída principal |
|---|---|---|
| `pesquisa-noticias` | Pesquisador | Título, Resumo, Fonte, **Ativos e indicadores envolvidos**, Palavras-chave |
| `apuracao-fontes` | Apurador | `## FONTES COLETADAS` (`- **Veículo**: Título (URL)`), `## NÚMEROS-CHAVE`, linha do tempo, consensos, contradições, lacunas |
| `verificacao-factual` | Verificador | Confirmados / disputados / não verificados, `## DADOS DE MERCADO CONFERIDOS`, `## FONTES`, `## ALERTA AO REDATOR` |
| `analise-mercado` | Analista de Investimentos | `## PAINEL DE MERCADO`, `## IMPACTO POR CLASSE DE ATIVO`, `## RISCOS E O QUE ACOMPANHAR`, `## GLOSSÁRIO` |
| `redacao-jornalistica` | Redator | Matéria de 450–700 palavras + `## O que isso significa para o investidor` + `## Referências` + aviso "não constitui recomendação de investimento" |

**Regras editoriais:**
- nunca inventar dados ou cotações;
- no mínimo 3 fontes;
- priorizar veículos especializados (Valor, InfoMoney, Bloomberg Línea, Reuters, E-Investidor...) e fontes oficiais (B3, CVM, BCB, RI das empresas);
- citações `[n]` consistentes com as referências;
- parágrafos corridos;
- tom imparcial e **sem recomendação de compra ou venda**.

---

## 6. Versões

| Versão | Arquivo / objeto | Arquitetura | Saída |
|---|---|---|---|
| V1 | `agente_curador.py` / `agente_noticias` | Um agente com as 4 skills (via `get_skill_instructions`) | `output/V1` |
| V2 | `agente_curador_v2.py` / `workflow` | 4 `passo_agente` sequenciais | `output/V2` |
| V3 | `agente_curador_v3.py` / `news_curator_workflow` | Pesquisa → `Loop` de apuração (3 fontes, até 3x) → Verificação → Redação | `output/V3` |
| V4 | `agente_curador_v4.py` / `research_pipeline_workflow` | Research Team (nacional + internacional) → Loop → `validar_fontes` → Verificação → Redação → `exportar_markdown` | `output/V4` |
| **V5** | `agente_curador_v5.py` / `investor_workflow` | Research Team de mercado (Brasil + global) → Loop (até 2x) → Validação → Verificação **com dados de mercado** → **Analista de Investimentos** → `consolidar_para_redacao` (verificação + análise) → Redação → Exportação | `output/V5` |

**Otimizações da V5 para o limite de tokens:**
- cada agente recebe só o texto da sua skill nas instruções (`ler_skill`), sem `skills=` e sem a requisição extra de `get_skill_instructions`;
- `LIMITES` de chamadas de ferramenta por papel (pesquisa 2, apuração 3, verificação 2, análise 3);
- `MAX_TENTATIVAS_APURACAO = 2`.

---

## 7. Interface (chat)

- `ui/app.py`:
  - título "📈 Notícias para Investidores";
  - `st.segmented_control` (key `versao`) para trocar a versão a qualquer momento;
  - histórico em `st.session_state.mensagens` (`papel`, `conteudo`, `versao`);
  - botões de sugestão (keys `sugestao_0..3`, via `tema_sugerido`);
  - erros de exceção ou de `status` ERROR aparecem no chat com `mensagem_erro_amigavel`.
- Painel de mercado na sidebar: `carregar_painel()` com `st.cache_data(ttl=900)` chama `obter_panorama` e `obter_indicadores` (métricas com variação do dia; Selic, CDI, IPCA e PTAX com data).
- `ui/registry.py`: `VERSOES` (V5..V1 → `Versao(rotulo, modulo, objeto, descricao, pipeline)`), `VERSAO_PADRAO = "V5"` e `carregar_workflow` com `lru_cache` (import sob demanda).

---

## 8. Execução e testes

```bash
uv sync
cp .env.example .env                          # GROQ_API_KEY
uv run python -m streamlit run ui/app.py
uv run python -m agente.agente_curador_v5
uv run python -m pytest                       # ~92 testes, ~3 s, sem rede
```

- As versões rodam **como módulo** a partir da raiz (`python -m agente.<arquivo>`).
- Testes:
  - `tests/conftest.py` define `GROQ_API_KEY` fictícia e um fixture **autouse** `mercado_simulado`, que substitui `_historico` e `_buscar_serie_bcb`. Nenhum teste acessa a rede.
  - Cobertura: ferramentas de mercado (tickers, IR, simulação, cotação, indicadores, falhas), passos (erro real do Groq, mensagens), estrutura de V2 a V5, busca sem `duckduckgo` e com limite, skill injetada na V5, contratos das skills e UI (painel, sugestões, troca de versão, erros, nova conversa, chave ausente).
- CI: `.github/workflows/testes.yml` (push na `main`, PRs, manual).

---

## 9. Limites do Groq (plano gratuito)

- Na conta do projeto, todos os modelos de chat têm **≤ 8.000 tokens/minuto**: `gpt-oss-20b`, `gpt-oss-120b` e `qwen/qwen3.8-27b` com 8K, `allam-2-7b` com 6K (consultado em 09/11/2026). Uma requisição maior que isso falha com **413**; várias seguidas dão **429**.
- Há também uma **cota diária de 200.000 tokens por modelo** (TPD). Algumas execuções completas consomem tudo. Quando acaba, `mensagem_erro_amigavel` informa quando libera; também dá para trocar `GROQ_MODEL_ID`, porque a cota é por modelo.
- O `gpt-oss` às vezes gera chamadas de ferramenta inválidas (400 `tool_use_failed`, ex.: `web_search` com `{"id": url}`). `GroqTolerante` em `comum.py` repete essas chamadas (`retries=2`), e `criar_busca` instrui o uso do argumento `query`.
- Cada chamada de ferramenta é uma nova requisição com todo o contexto, então um workflow completo leva **vários minutos**, a maior parte esperando a cota.
- Mitigações: poucos resultados por busca, `tool_call_limit`, skill injetada (V5), retries do SDK e mensagens de erro claras. Para ganhar velocidade de verdade, use o plano Developer do Groq ou outro modelo/provedor.

---

## 10. Windows e Smart App Control

A máquina de desenvolvimento (Windows 11 Home) tem o **Smart App Control ativado**, que bloqueia binários sem assinatura:
- o Python baixado pelo uv: `DLL load failed while importing unicodedata/_socket: Uma política de Controle de Aplicativo bloqueou este arquivo`;
- os `.exe` de `.venv\Scripts` (ex.: `streamlit.exe`): `os error 4551`.

**Solução:** usar o Python oficial (assinado pela PSF, `py install 3.13`), `python-preference = "only-system"` e sempre `python -m <ferramenta>`. Se o `.venv` foi criado com o Python do uv, apague-o e rode `uv sync`.

---

## 11. Pontos em aberto

1. Execuções ponta a ponta com LLM são lentas no plano gratuito (§9). Considerar streaming de progresso por etapa na UI.
2. Fundos de investimento tradicionais (dados da CVM) ainda não têm ferramenta própria; FIIs e ETFs são cobertos pelo `cotacao_ativo`.
3. Os testes não avaliam a qualidade das matérias. Uma suíte opcional de avaliação com LLM (fora do CI) seria o próximo passo.
4. Agentes são definidos por versão de propósito (comparabilidade); o compartilhado fica em `comum.py`, `passos.py` e `ferramentas_mercado.py`.
