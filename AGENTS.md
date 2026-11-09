# AGENTS.md

Instruções para agentes de código (Claude Code, Codex, Cursor etc.) que trabalham neste repositório. Leia também [CONTEXT.md](CONTEXT.md) para o contexto completo do projeto.

## Resumo do projeto

Curadoria de notícias com IA: dado um tema, uma cadeia de agentes **Agno** (LLM Groq `openai/gpt-oss-20b` + busca DuckDuckGo) pesquisa, apura fontes, verifica fatos e redige uma matéria jornalística em Markdown. Cada versão em `agente/` é uma arquitetura diferente: V1 monolítica, V2 workflow sequencial, V3 workflow com `Loop` de apuração, V4 com Research Team (`Team`), validação de fontes e exportação determinística. A UI Streamlit em `ui/` permite escolher a versão.

## Setup e comandos

```bash
uv sync                                    # instala dependências (Python 3.12.11)
cp .env.example .env                       # preencher GROQ_API_KEY
uv run python -m agente.agente_curador_v4  # executa o pipeline V4 com o tema de exemplo
uv run streamlit run ui/app.py             # interface web
```

- Rode as versões **como módulo a partir da raiz** (`python -m agente.<arquivo>`); `python agente/arquivo.py` falha porque o import de `agente.comum` depende do pacote.
- **Nunca** commite o `.env` nem imprima a chave.
- Rodar os agentes faz chamadas reais à API do Groq e buscas na web (custo/rate limit). Não execute pipelines completos sem necessidade; prefira validar com `python -m py_compile` ou testando funções puras.
- Não há suíte de testes. Ao adicionar lógica pura (ex.: `contar_fontes`, `validar_fontes`), crie testes `pytest` que não chamem o LLM.
- Nesta máquina Windows, o Python do uv pode ser bloqueado pelo Controle de Aplicativo (`ImportError: DLL load failed while importing _socket`). Se ocorrer, não é bug do projeto — reporte ao usuário.

## Mapa do código

| Caminho | Função |
|---|---|
| `agente/comum.py` | Caminhos (`BASE_DIR`, `SKILLS_DIR`, `OUTPUT_DIR`), `criar_modelo`, `carregar_skills`, `criar_file_tools`, `diretorio_saida`, `verificar_api_key`, `contar_fontes` |
| `agente/agente_curador.py` | V1 — `agente_noticias` |
| `agente/agente_curador_v2.py` | V2 — `workflow` |
| `agente/agente_curador_v3.py` | V3 — `news_curator_workflow` |
| `agente/agente_curador_v4.py` | V4 — `research_pipeline_workflow`, `research_team`, `validar_fontes`, `exportar_markdown` |
| `skills/<nome>/SKILL.md` | Instruções de cada etapa, carregadas via `LocalSkills` |
| `ui/registry.py` | Registro das versões exibidas na UI |
| `ui/app.py`, `ui/components/` | App Streamlit |

## Convenções

- **Idioma:** domínio, prompts, skills, nomes de variáveis e mensagens em **português brasileiro**.
- **Versionamento por arquivo:** cada nova arquitetura é um novo `agente/agente_curador_vN.py`. Não transforme versões antigas na nova — elas existem para comparação. Correções de bug nelas são bem-vindas.
- **Use `agente/comum.py`** para modelo, skills, caminhos e saída; não recrie `Groq(...)`, `Path(__file__)...` ou `load_dotenv` nos módulos de versão. Cada versão grava em `output/VN` (`criar_file_tools("VN")` ou `diretorio_saida("VN")`).
- **Registrar na UI:** toda nova versão deve exportar um objeto com `.run()` / `.print_response()` e ser adicionada a `WORKFLOWS` em `ui/registry.py`.
- **`__main__`:** chame `verificar_api_key()` antes de executar.
- **Constantes** (`MIN_FONTES`, `MAX_TENTATIVAS_APURACAO`) em maiúsculas no topo do módulo e interpoladas nas instruções com f-strings, para manter prompt e código sincronizados.
- **Agentes:** `Agent(name=..., model=criar_modelo(), skills=shared_skills, instructions=[...], tools=[...], add_datetime_to_context=True, markdown=True)`. As instruções devem pedir para carregar a skill com `get_skill_instructions` antes de executar.
- **Prefira passos determinísticos** (`Step(executor=funcao)`) para regras verificáveis em código — contagem de fontes, gravação de arquivos — em vez de confiar no LLM (padrão da V4).
- **Commits:** mensagens descritivas (evite `#`). Não commitar `.venv/`, `output/`, `.env`.

## Skills

- Formato: `skills/<nome-kebab-case>/SKILL.md` com frontmatter YAML (`name`, `description`, `metadata.version`, `metadata.tags`) seguido de: Quando usar / Entrada esperada / Processo / Formato de saída / Regras.
- O `name` no frontmatter deve ser igual ao nome da pasta e ao nome usado nas instruções dos agentes.
- **Os cabeçalhos de saída são contrato.** `contar_fontes` procura `## FONTES COLETADAS`, veículos em `**negrito**` e URLs; a V4 injeta `## VALIDAÇÃO DE FONTES`. Ao alterar o formato de uma skill, atualize o parsing e as instruções dos agentes, e vice-versa.
- Ao mudar uma skill, incremente `metadata.version`.

## Regras editoriais (não negociáveis)

Qualquer alteração em prompts ou skills deve preservar:
- Nunca inventar dados, nomes ou citações.
- Mínimo de 3 fontes distintas, com veículo e URL.
- Classificação CONFIRMADO / DISPUTADO / NÃO VERIFICADO na verificação factual.
- Matéria de 400–600 palavras, em parágrafos (sem bullets no corpo), imparcial, com citações `[n]` e seção `## Referências` consistente.

## Manutenção da documentação

Ao mudar arquitetura, versões, comandos ou contratos de skills, atualize `CONTEXT.md`, este arquivo e o `README.md`.
