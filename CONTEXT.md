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
| Dados de mercado | API pública de gráficos do Yahoo Finance, chamada direto por `urllib` (endpoints `spark` em lote e `chart` intradiário; B3 com sufixo `.SA`, EUA, índices, câmbio, cripto, commodities) + API SGS do Banco Central |
| API | FastAPI + Uvicorn (`python -m api`), JSON + Server-Sent Events |
| Interface | **Quantum Terminal**: HTML, CSS e JavaScript puros em `web/`, sem build (CDN: Google Fonts, Lucide 0.469.0, marked 12.0.2, DOMPurify 3.1.6) |
| Testes | `pytest` + `fastapi.testclient.TestClient`; CI no GitHub Actions |
| Configuração | `.env` (`GROQ_API_KEY`; opcionais `GROQ_MODEL_ID`, `BUSCA_BACKEND`), modelo em `.env.example` |

`fastapi` também é exigido pelo próprio `agno.workflow`. O **yfinance foi removido**: ele busca um cookie/crumb do Yahoo que dava timeout (~30 s por consulta) e, com consultas paralelas, derrubava o DNS. Os endpoints diretos respondem em < 0,5 s.

---

## 3. Estrutura do repositório

```text
News_Analytics_Platform/
├── agente/
│   ├── comum.py                 # modelo, busca, skills, caminhos, contar_fontes, ler_skill, erros amigáveis
│   ├── passos.py                # passo_agente, validar_fontes, exportar_markdown, slug, condição do loop
│   ├── ferramentas_mercado.py   # MercadoFinanceiroTools + funções de cotação/indicadores/simulação
│   ├── uso_groq.py              # MedidorGroq: tokens 24 h, TPM e RPD por modelo (card da sidebar)
│   ├── agente_curador.py        # V1 (agente_noticias)
│   ├── agente_curador_v2.py     # V2 (workflow)
│   ├── agente_curador_v3.py     # V3 (news_curator_workflow)
│   ├── agente_curador_v4.py     # V4 (research_pipeline_workflow)
│   └── agente_curador_v5.py     # V5 — Investidor (investor_workflow)
├── skills/                      # SKILL.md com frontmatter YAML
│   ├── pesquisa-noticias/  apuracao-fontes/  verificacao-factual/
│   ├── analise-mercado/    redacao-jornalistica/
├── api/
│   ├── servidor.py              # FastAPI: /api/* + serve web/ ("/" e "/static")
│   ├── execucao.py              # Tarefa, GerenciadorDeTarefas, executar(): eventos do pipeline
│   ├── registry.py              # VERSOES, VERSAO_PADRAO="V5", carregar_workflow (lazy)
│   └── __main__.py              # python -m api [--host] [--port] [--reload]
├── web/
│   ├── index.html               # app de página única (sidebar, painel, matérias, watchlist, simulador, console)
│   ├── css/quantum.css          # tokens e componentes do Quantum Terminal
│   └── js/app.js                # navegação, mercado, gráficos SVG, simulador, matérias, chat via SSE
├── design/                      # design_system1-3.html + referências (DS/, components/)
├── tests/                       # conftest (mercado simulado), api, comum, passos, ferramentas, skills, versões
├── .github/workflows/testes.yml # CI: Ubuntu/Windows × Python 3.12/3.13
├── output/                      # matérias geradas (ignorado pelo git)
└── .env.example / .python-version / pyproject.toml / uv.lock
```

---

## 4. Módulos compartilhados

### `agente/comum.py`
- Caminhos: `BASE_DIR`, `SKILLS_DIR`, `OUTPUT_DIR`. `load_dotenv` roda no import.
- `criar_modelo()`: `GroqTolerante` no primeiro modelo com cota (`modelo_disponivel()`), `max_retries=TENTATIVAS_API` (2, retries do SDK para 429 por minuto), `retries=len(modelos)+1` (Agno) e `http_client=cliente_http_groq()` (cliente compartilhado com o medidor de tokens).
- **Cota diária e modelos reserva**: `modelos_configurados()` = `GROQ_MODEL_ID` + `GROQ_MODELOS_RESERVA` (padrão `openai/gpt-oss-120b`; vazio desativa). Registro compartilhado `_cota_esgotada_ate` (modelo → quando libera), com `registrar_cota_esgotada`, `modelo_disponivel`, `situacao_cota`, `segundos_ate_liberar` (lê o "try again in 4m29s") e `resumo_cota_esgotada`.
- `GroqTolerante`:
  - num 429 de **cota diária (TPD)**, marca o modelo como esgotado para todos os agentes e troca `self.id` para o próximo modelo com cota, repetindo na hora. Sem reserva, devolve não repetível (falha rápida);
  - antes de cada `invoke`/`invoke_stream`, `_escolher_modelo()` pula modelos esgotados (inclusive em agentes criados antes) e levanta `CotaEsgotada` se não houver nenhum;
  - repete chamadas de ferramenta inválidas (400 `tool_use_failed`).
- `BuscaTolerante` (`criar_busca()`): `web_search`/`search_news` devolvem `{"resultados": [], "aviso": ...}` em vez de levantar `DDGSException: No results found.`.
- `criar_busca()`: `WebSearchTools(backend="auto", fixed_max_results=MAX_RESULTADOS_BUSCA)` (5). **Não use `DuckDuckGoTools`**: ele fixa o backend `duckduckgo`, que parou de retornar resultados.
- `LIMITE_CHAMADAS_FERRAMENTAS` (4): `tool_call_limit` padrão da V4.
- `carregar_skills()`, `ler_skill(nome)` (corpo do SKILL.md sem o frontmatter), `diretorio_saida`, `criar_file_tools`, `contar_fontes`, `verificar_api_key`, `mensagem_erro_amigavel` (traduz 413/429/401 do Groq).

### `agente/uso_groq.py`
- `MedidorGroq.hook_resposta` é um *event hook* do httpx em toda resposta de `/chat/completions`. Ele registra os cabeçalhos `x-ratelimit-*` (TPM limite/restante, RPD limite/restante), o `usage.total_tokens` (respostas 200) e, nos 429 de TPD, o "Limit/Used" oficial. Nunca levanta exceção.
- `uso(modelo)` → `tokens_24h` (janela móvel: contagem do app, corrigida pelo valor oficial do 429 quando existe), `tpd_limite` (200 mil, o padrão do plano gratuito), `tpm_restante/limite` (válido por ~2 min; depois volta ao limite), `rpd_restante/limite` e `fonte_24h`.
- O histórico é salvo em `output/.uso_groq.json`, no máximo a cada 5 s.

### `agente/passos.py`
- `passo_agente(nome, agente_ou_team, descricao, max_retries=1)`: um `Step` com executor que roda o agente **sem streaming** e verifica `RunStatus.error`. Se falhar, levanta `ErroDoAgente` com a causa real. **Por quê:** no Agno 2.4.8, quando um agente falha dentro de `Step(agent=...)`, o erro real (ex.: 413 do Groq) é escondido por `'NoneType' object has no attribute 'parent_run_id'`. V2 a V5 usam esse wrapper.
- **Cancelamento**: `CONTROLE_EXECUCAO` (ContextVar) guarda o controle da execução corrente (a `Tarefa` da API). `passo_agente` chama `verificar_cancelamento()` antes e depois do agente e passa `run_id=novo_run_id()`, registrado no controle, para o agente poder ser interrompido pelo cancelamento do Agno. `exportar_markdown` também verifica, para pesquisa cancelada não gerar arquivo. Sem controle (ex.: rodando no terminal), tudo funciona como antes.
- `criar_condicao_fontes(min)`, `validar_fontes(step_input, min, tentativas)`, `slug`, `exportar_markdown(step_input, pasta)`.

### `agente/ferramentas_mercado.py`
- Funções puras: `normalizar_ticker` (`petr4` → `PETR4.SA`; apelidos como IBOV, DOLAR, BITCOIN, BRENT), `aliquota_ir` (tabela regressiva de 22,5% a 15%), `simular_renda_fixa`, `resumir_historico`.
- Acesso a dados, isolado para os testes:
  - `_yahoo_json(url)`: urllib com User-Agent, timeout de 12 s e **semáforo de 4 conexões** (`_limite_yahoo`);
  - `_historicos_lote(tickers, periodo)`: fechamentos diários de **vários ativos numa requisição** (endpoint `spark`, até 20 por chamada); `_historico` usa o lote;
  - `_serie(ticker, periodo, intervalo)`: pontos com horário no fuso da bolsa (endpoint `chart`), para os gráficos;
  - `_buscar_serie_bcb(codigo)` → `ultimo_valor_sgs(codigo, get_json)`: SGS 432 Selic, 4389 CDI, 13522 IPCA 12m, 1 PTAX. **Para a 4389, `ultimos/1` responde HTTP 304 sem corpo**; o fallback consulta os últimos 120 dias por intervalo de datas.
- Alto nível: `obter_cotacoes(lista)` (lote, mantém a ordem), `obter_cotacao`, `obter_historico(ticker, periodo)` (`PERIODOS_GRAFICO`: 1d/5m, 5d/30m, 1mo, 6mo, 1y), `obter_indicadores`, `obter_panorama`. Nunca levantam exceção; em caso de falha devolvem `{"erro": ...}`.
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

## 7. API e interface (Quantum Terminal)

O Streamlit foi substituído por uma API FastAPI que também serve o front-end em HTML/CSS/JS puro, seguindo o design system escolhido (`design/design_system1.html`, **Quantum Terminal**).

### Rotas (`api/servidor.py`)

| Rota | Descrição |
|---|---|
| `GET /` | `web/index.html` (estáticos em `/static`) |
| `GET /api/status` | chave configurada?, modelo **ativo** (primeiro com cota), `cota` (situação por modelo), `uso_groq` (tokens/limites por modelo), backend de busca, tarefas em execução |
| `POST /api/groq/sondar` | chamada mínima (`max_tokens=1`, ~10 tokens) em cada modelo para atualizar os limites no medidor |
| `GET /api/versoes` | V1–V5 (`registry.VERSOES`, sem detalhes internos) e a padrão |
| `GET /api/mercado` | `panorama` + `indicadores` (cache de 15 min) |
| `GET /api/mercado/cotacoes?tickers=A,B` | até 20 tickers; os que não estão em cache são buscados **em um único lote** (cache de 5 min por ticker) |
| `GET /api/mercado/historico/{ticker}?periodo=` | `1d`, `5d`, `1mo`, `6mo` ou `1y`: pontos para o gráfico (cache de 5 min) |
| `POST /api/simulacao/renda-fixa` | `{valor, taxa_anual_pct, meses, isento_ir}` validados por Pydantic |
| `POST /api/perguntas` | `{tema, versao}` → `202 {id, etapas}`; 503 sem `GROQ_API_KEY`; **429 se nenhum modelo tiver cota diária** |
| `POST /api/perguntas/{id}/cancelar` | cancela a pesquisa (409 se já terminou ou já foi cancelada) |
| `GET /api/perguntas/{id}` | estado completo (eventos, conteúdo, erro) |
| `GET /api/perguntas/{id}/eventos` | **Server-Sent Events** com o progresso; `: ping` a cada 15 s |
| `GET /api/materias` e `GET /api/materias/{versao}/{arquivo}` | matérias em `output/V*/*.md`, com validação contra *path traversal* |
| `GET /api/docs` | Swagger da API |

- **Cache** em memória (`Cache`): **não guarda respostas com `erro`, nem parciais** (ex.: só o CDI falhou), para tentar de novo na próxima chamada.
- **Execução** (`api/execucao.py`): cada pergunta é uma `Tarefa` numa thread. `executar()` roda o workflow com `stream=True, stream_events=True` e traduz os eventos do Agno de **primeiro nível** (`StepStarted/Completed`, `LoopExecutionStarted/Completed`, `LoopIterationStarted`, `StepErrorEvent`, `WorkflowCompleted/ErrorEvent`) em eventos simples: `inicio` (com as etapas e os `ROTULOS`), `etapa` (iniciada/concluída/erro + duração), `tentativa` (iteração do loop), `conteudo` (markdown), `erro` (via `mensagem_erro_amigavel`) `cancelado` (emitido na hora do cancelamento) e `fim` (com `cancelada`). Passos internos do loop (ex.: `apuracao`) são ignorados. Para um `Agent` (V1), há uma etapa só: "Agente único".
- **Cancelamento** (`Tarefa.cancelar()`): marca a tarefa, emite `cancelado` e chama `cancelar_run_do_agno` para cada `run_id` registrado. O cancelamento do Agno **ignora runs ainda não registrados** e o `register_run` zera o estado; por isso, se o agente ainda não começou, uma *thread* curta espera o registro (via `get_active_runs()`) e então cancela. `executar()` fecha o *stream* do workflow no próximo evento e não emite `conteudo` nem `erro` para tarefas canceladas. Limitação: a chamada ao modelo já em andamento termina antes de parar.

### Front-end (`web/`)

- Página única com rotas por hash (`#painel`, `#materias`, `#watchlist`, `#simulador`); sidebar recolhível; fita de cotações; relógio do pregão da B3 (10h–17h55 BRT, dias úteis).
- **Painel**: KPIs (Ibovespa e dólar com *sparkline*, Selic com CDI, IPCA com leitura da meta), gráfico SVG do Ibovespa (1D/5D/1M/6M/1A, com mira e tooltip), últimas matérias, mini simulador e watchlist.
- **Cancelar**: durante a execução, o botão de enviar vira *Cancelar* (vermelho), há um botão no cartão de telemetria e a tecla Esc também cancela. Se o envio ainda está em andamento, um `AbortController` aborta o `fetch`; senão, `POST /cancelar`. No evento `cancelado`, as etapas restantes ficam riscadas e a interface é liberada.
- **Card Tokens · Groq** (sidebar): para cada modelo, barra de 24 h (tokens/200 mil, amarela a partir de 70% e vermelha a partir de 90%), tokens livres por minuto, requisições restantes no dia e estado (ativo / reserva / esgotado · ~min). Atualiza com o `/api/status` a cada 15 s; o botão ⟳ chama `/api/groq/sondar`.
- **Console da redação**: seletor V1–V5 (bloqueado durante a execução), sugestões, atalhos na sidebar ("Perguntar sobre"), cronômetro e **telemetria do pipeline**, com as etapas reais acendendo via SSE. A matéria chega renderizada (marked com `breaks: true` + DOMPurify; os links abrem em nova aba).
- **Watchlist** salva no `localStorage` (padrão: PETR4, VALE3, ITUB4, BBAS3, WEGE3, MXRF11, IVVB11; máx. 20), **Simulador** completo usando a API e **Matérias** com lista e leitor.
- Preferências locais: versão, watchlist e sidebar recolhida (`localStorage`, com `try/catch`).
- Segurança: todo texto vindo da API passa por `esc()`, e o markdown gerado pelo LLM é sanitizado com DOMPurify.
- Responsivo: até 1080 px o console vira gaveta; até 760 px a sidebar também. Respeita `prefers-reduced-motion`.

---

## 8. Execução e testes

```bash
uv sync
cp .env.example .env                          # GROQ_API_KEY
uv run python -m api                          # http://127.0.0.1:8000
uv run python -m agente.agente_curador_v5
uv run python -m pytest                       # 115 testes, ~1 s, sem rede
```

- As versões rodam **como módulo** a partir da raiz (`python -m agente.<arquivo>`).
- Testes:
  - `tests/conftest.py` define `GROQ_API_KEY` fictícia e um fixture **autouse** `mercado_simulado`, que substitui `_historicos_lote`, `_serie` e `_buscar_serie_bcb`. O fixture `funcoes_reais` dá acesso às implementações reais, para testar o *parsing* com `_yahoo_json` simulado. Nenhum teste acessa a rede.
  - `test_cota.py` (troca de modelo, falha rápida, mensagens, busca tolerante), `test_cancelamento.py` (passos, corrida com o `register_run` do Agno, API até o fim sem matéria), `test_uso_groq.py` (hook do httpx com `MockTransport`, 429 oficial, janela de 24 h, persistência, sondagem).
  - `test_api.py`: front servido, status, versões, mercado (cache, lote, validações), histórico, simulação, matérias (inclusive *path traversal*) e perguntas com **workflows falsos que imitam os eventos do Agno** (etapas, loop, erro, SSE até o fim, agente único, chave ausente).
  - Demais arquivos: ferramentas de mercado (tickers, IR, simulação, *parsing* de spark/chart, lote, fallback do BCB), passos, estrutura de V2 a V5, busca e skills.
- CI: `.github/workflows/testes.yml` (push na `main`, PRs, manual).

---

## 9. Limites do Groq (plano gratuito)

- Na conta do projeto, todos os modelos de chat têm **≤ 8.000 tokens/minuto**: `gpt-oss-20b`, `gpt-oss-120b` e `qwen/qwen3.8-27b` com 8K, `allam-2-7b` com 6K (consultado em 09/11/2026). Uma requisição maior que isso falha com **413**; várias seguidas dão **429**.
- Há também uma **cota diária de 200.000 tokens por modelo** (TPD). Algumas execuções completas consomem tudo. Quando acaba, `mensagem_erro_amigavel` informa quando libera; também dá para trocar `GROQ_MODEL_ID`, porque a cota é por modelo.
- O `gpt-oss` às vezes gera chamadas de ferramenta inválidas (400 `tool_use_failed`, ex.: `web_search` com `{"id": url}`). `GroqTolerante` em `comum.py` repete essas chamadas (`retries=2`), e `criar_busca` instrui o uso do argumento `query`.
- Cada chamada de ferramenta é uma nova requisição com todo o contexto, então um workflow completo leva **vários minutos**, a maior parte esperando a cota.
- Limites por modelo vistos nos cabeçalhos: **8.000 TPM** e **1.000 requisições/dia**. O TPD (200 mil) só aparece nas mensagens 429; o card da sidebar mostra os três.
- **Troca automática para os modelos reserva** quando a cota diária acaba (ver §4) e recusa imediata (429) quando todos estão esgotados.
- Mitigações: poucos resultados por busca, `tool_call_limit`, skill injetada (V5), retries do SDK e mensagens de erro claras. Para ganhar velocidade de verdade, use o plano Developer do Groq ou outro modelo/provedor.

---

## 10. Windows e Smart App Control

A máquina de desenvolvimento (Windows 11 Home) tem o **Smart App Control ativado**, que bloqueia binários sem assinatura:
- o Python baixado pelo uv: `DLL load failed while importing unicodedata/_socket: Uma política de Controle de Aplicativo bloqueou este arquivo`;
- os `.exe` de `.venv\Scripts` (ex.: `uvicorn.exe`): `os error 4551`. Por isso a API sobe com `python -m api`.

**Solução:** usar o Python oficial (assinado pela PSF, `py install 3.13`), `python-preference = "only-system"` e sempre `python -m <ferramenta>`. Se o `.venv` foi criado com o Python do uv, apague-o e rode `uv sync`.

---

## 11. Pontos em aberto

1. Execuções ponta a ponta com LLM são lentas no plano gratuito (§9); a UI mostra o progresso por etapa, mas o tempo total continua alto.
2. As tarefas ficam só em memória: reiniciar o servidor perde as perguntas em andamento (as matérias já salvas em `output/` permanecem). Não há autenticação: a API sobe em `127.0.0.1` por padrão.
3. Fundos de investimento tradicionais (dados da CVM) ainda não têm ferramenta própria; FIIs e ETFs são cobertos pelo `cotacao_ativo`.
4. Os testes não avaliam a qualidade das matérias. Uma suíte opcional de avaliação com LLM (fora do CI) seria o próximo passo. O JavaScript do front não tem testes automatizados; foi verificado no Chrome headless (sem erros de console, fluxo do chat com workflow falso, 390/900/1600 px).
5. Agentes são definidos por versão de propósito (comparabilidade); o compartilhado fica em `comum.py`, `passos.py` e `ferramentas_mercado.py`.
