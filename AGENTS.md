# AGENTS.md

Instruções para agentes de código (Claude Code, Codex, Cursor etc.) que trabalham neste repositório. Leia também [CONTEXT.md](CONTEXT.md) para o contexto completo.

## Resumo do projeto

Plataforma de notícias **para investidores** (ações, renda fixa, renda variável, fundos, câmbio, cripto, economia; outros temas também são aceitos). Agentes **Agno** + Groq pesquisam, apuram, checam fatos, cruzam com **dados reais de mercado** (yfinance + Banco Central) e redigem a matéria. As versões V1 a V5 em `agente/` são arquiteturas diferentes; a **V5 — Investidor** é a principal. A UI Streamlit é um chat com seletor de versão e painel de mercado.

## Setup e comandos

```bash
uv sync                                     # Python 3.12/3.13 do sistema
cp .env.example .env                        # GROQ_API_KEY
uv run python -m pytest                     # ~3 s, sem rede: rode antes de concluir qualquer mudança
uv run python -m streamlit run ui/app.py    # interface
uv run python -m agente.agente_curador_v5   # V5 no terminal
```

- Rode as versões **como módulo a partir da raiz** (`python -m agente.<arquivo>`).
- **Nunca** commite o `.env` nem imprima a chave.
- **Windows / Smart App Control:** nunca use o Python gerenciado pelo uv (`python-preference = "only-system"`) e chame ferramentas via `python -m` (não pelos `.exe` de `.venv\Scripts`). O erro `Uma política de Controle de Aplicativo bloqueou este arquivo` tem essa causa; não é bug do projeto.
- **Custo:** rodar agentes chama a API do Groq (plano gratuito: 8.000 tokens/minuto por modelo) e faz buscas reais. Um workflow completo leva minutos. Só execute ponta a ponta quando necessário; prefira testes.

## Mapa do código

| Caminho | Função |
|---|---|
| `agente/comum.py` | `criar_modelo`, `criar_busca`, `carregar_skills`, `ler_skill`, caminhos, `contar_fontes`, `mensagem_erro_amigavel`, limites |
| `agente/passos.py` | `passo_agente` (expõe o erro real), `validar_fontes`, `exportar_markdown`, `slug`, `criar_condicao_fontes` |
| `agente/ferramentas_mercado.py` | `MercadoFinanceiroTools` e funções `obter_cotacao`/`obter_indicadores`/`obter_panorama`/`simular_renda_fixa` |
| `agente/agente_curador*.py` | V1 `agente_noticias`, V2 `workflow`, V3 `news_curator_workflow`, V4 `research_pipeline_workflow`, V5 `investor_workflow` |
| `skills/<nome>/SKILL.md` | pesquisa-noticias, apuracao-fontes, verificacao-factual, analise-mercado, redacao-jornalistica |
| `ui/registry.py` | `VERSOES`, `VERSAO_PADRAO`, `carregar_workflow` (lazy) |
| `ui/app.py`, `ui/components/sidebar.py` | Chat, sugestões, painel de mercado |
| `tests/` | pytest; `conftest.py` simula o mercado (autouse) |

## Convenções

- **Idioma:** português brasileiro em domínio, prompts, skills, variáveis e mensagens.
- **Versionamento por arquivo:** uma nova arquitetura é um novo `agente/agente_curador_vN.py`. Não transforme versões antigas na nova; correções de bug nelas são bem-vindas.
- **Use os módulos compartilhados:** nada de `Groq(...)`, `DuckDuckGoTools`, `load_dotenv` ou `Path(__file__)` nos módulos de versão.
  - **Busca:** sempre `criar_busca()`. O backend `duckduckgo` está quebrado e os resultados precisam ser limitados por causa dos tokens.
  - **Agentes em workflow:** sempre `passo_agente(...)`, nunca `Step(agent=...)` ou um agente solto em `steps=`. O Agno 2.4.8 esconde o erro real atrás de `parent_run_id`.
  - **Agentes com ferramentas:** defina `tool_call_limit`.
- **Orçamento de tokens:** toda requisição precisa caber em 8.000 tokens. Prefira injetar só a skill necessária (`ler_skill`, padrão da V5), limitar resultados e chamadas de ferramenta, e preferir passos determinísticos (`Step(executor=...)`) para regras verificáveis (contagem de fontes, consolidação, gravação de arquivos).
- **Dados de mercado:** números vêm das ferramentas (yfinance/BCB), nunca do LLM. Novas fontes vão em `ferramentas_mercado.py` com acesso a rede isolado em funções `_privadas` (para o fixture de testes simular), retornando `{"erro": ...}` em vez de levantar exceção.
- **Registrar na UI:** nova versão → entrada `Versao(...)` em `VERSOES`, mais testes de estrutura em `tests/test_versoes.py`.
- **`__main__`:** chame `verificar_api_key()` antes de executar.
- **Commits:** mensagens descritivas (evite `#`); não commitar `.venv/`, `output/`, `.env`.

## Skills

- Formato: `skills/<nome-kebab-case>/SKILL.md` com frontmatter (`name` = nome da pasta, `description`, `metadata.version`, `metadata.tags`).
- Mantenha as skills **enxutas**: o texto delas entra no prompt e consome cota de tokens.
- **Os cabeçalhos de saída são contrato:** `contar_fontes` lê `## FONTES COLETADAS` com `**Veículo**` e URLs; a V4/V5 injeta `## VALIDAÇÃO DE FONTES`; a V5 consolida `# RELATÓRIO DE VERIFICAÇÃO` + `# ANÁLISE DE MERCADO`. A skill `analise-mercado` cita ferramentas pelo nome, e um teste garante que elas existem. Ao mudar um formato, atualize código, instruções e testes juntos.
- Ao mudar uma skill, incremente `metadata.version`.

## Regras editoriais (não negociáveis)

- Nunca inventar dados, cotações, nomes ou citações.
- **Nunca recomendar compra ou venda**; matérias financeiras terminam com "_Conteúdo informativo; não constitui recomendação de investimento._"
- No mínimo 3 fontes distintas, com veículo e URL; priorizar veículos especializados e fontes oficiais (B3, CVM, BCB).
- Classificação CONFIRMADO / DISPUTADO / NÃO VERIFICADO.
- Matéria em parágrafos (sem bullets no corpo), citações `[n]` consistentes com `## Referências`, seção "O que isso significa para o investidor" em temas financeiros.

## Testes

- Nenhum teste pode chamar o LLM, a web ou as APIs de mercado. O `conftest.py` já simula `_historico` e `_buscar_serie_bcb` e define uma chave fictícia.
- UI: `streamlit.testing.v1.AppTest`, substituindo `registry.carregar_workflow` por um workflow falso via `monkeypatch`.

## Manutenção da documentação

Ao mudar arquitetura, versões, comandos, limites ou contratos de skills, atualize `CONTEXT.md`, este arquivo e o `README.md`.
