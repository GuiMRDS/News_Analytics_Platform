# AGENTS.md

Instruções para agentes de código (Claude Code, Codex, Cursor etc.) que trabalham neste repositório. Leia também [CONTEXT.md](CONTEXT.md) para o contexto completo do projeto e a lista de problemas conhecidos.

## Resumo do projeto

Curadoria de notícias com IA: dado um tema, uma cadeia de agentes **Agno** (LLM Groq `openai/gpt-oss-20b` + busca DuckDuckGo) pesquisa, apura fontes, verifica fatos e redige uma matéria jornalística em Markdown. Cada versão em `agente/` é uma arquitetura diferente (V1 monolítica, V2 workflow sequencial, V3 workflow com `Loop` de apuração). A UI Streamlit em `ui/` permite escolher a versão.

## Setup e comandos

```bash
uv sync                               # instala dependências (Python 3.12.11)
python agente/agente_curador_v3.py    # executa o pipeline V3 com o tema de exemplo
streamlit run ui/app.py               # interface web
```

- Requer `.env` na raiz com `GROQ_API_KEY=...`. **Nunca** commite o `.env` nem imprima a chave.
- Rodar os agentes faz chamadas reais à API do Groq e buscas na web (custo/rate limit). Não execute pipelines completos sem necessidade; prefira validar com import/compilação (`python -c "import agente.agente_curador_v3"`) ou funções puras.
- Não há suíte de testes. Se adicionar lógica pura (ex.: `contar_fontes`, `fontes_suficientes`), considere testes com `pytest` que não chamem o LLM.

## Mapa do código

| Caminho | Função |
|---|---|
| `agente/agente_curador.py` | V1 — `agente_noticias` (Agent único) |
| `agente/agente_curador_v2.py` | V2 — `workflow` (4 agentes em sequência) |
| `agente/agente_curador_v3.py` | V3 — `news_curator_workflow` (Step + Loop, `MIN_FONTES`, `contar_fontes`) |
| `skills/<nome>/SKILL.md` | Instruções de cada etapa, carregadas via `LocalSkills` |
| `ui/registry.py` | Registro das versões exibidas na UI |
| `ui/app.py`, `ui/components/` | App Streamlit |

## Convenções

- **Idioma:** domínio, prompts, skills, nomes de variáveis e mensagens em **português brasileiro**. Mantenha esse padrão (ex.: `pesquisador`, `apurador`, `fontes_suficientes`).
- **Versionamento por arquivo:** cada nova arquitetura é um novo arquivo `agente/agente_curador_vN.py`. Não reescreva versões anteriores para virar a nova — elas existem para comparação. Correções de bug nas antigas são bem-vindas.
- **Registrar na UI:** toda nova versão deve exportar um objeto com `.run()` / `.print_response()` e ser adicionada a `WORKFLOWS` em `ui/registry.py`.
- **Caminhos:** resolva a partir da raiz do repo (`BASE_DIR = Path(__file__).resolve().parent.parent`), como na V3. A pasta de skills é `BASE_DIR / "skills"`. Use um diretório de saída próprio por versão (`output/VN`).
- **Configuração no topo do módulo:** constantes como `MIN_FONTES` e `MAX_TENTATIVAS_APURACAO` em maiúsculas; interpolar nas instruções com f-strings para manter prompt e código sincronizados.
- **Agentes:** padrão atual — `Agent(name=..., model=Groq(id="openai/gpt-oss-20b", api_key=GROQ_API_KEY), skills=shared_skills, instructions=[...], tools=[...], add_datetime_to_context=True, markdown=True)`. As instruções devem pedir para carregar a skill com `get_skill_instructions` antes de executar.
- **Commits:** mensagens descritivas (evite `#`). Não commitar `.venv/`, `output/`, `.env`.

## Skills

- Formato: `skills/<nome-kebab-case>/SKILL.md` com frontmatter YAML (`name`, `description`, `metadata.version`, `metadata.tags`) seguido de: Quando usar / Entrada esperada / Processo / Formato de saída / Regras.
- O `name` no frontmatter deve ser igual ao nome da pasta e ao nome usado nas instruções dos agentes.
- **Os cabeçalhos de saída são contrato.** Ex.: a V3 conta fontes procurando `## FONTES COLETADAS`, veículos em `**negrito**` e URLs. Ao alterar o formato de uma skill, atualize o código que faz parsing (`contar_fontes`) e as instruções dos agentes, e vice-versa.
- Ao mudar uma skill, incremente `metadata.version`.

## Regras editoriais (não negociáveis)

Qualquer alteração em prompts ou skills deve preservar:
- Nunca inventar dados, nomes ou citações.
- Mínimo de 3 fontes distintas, com veículo e URL.
- Classificação CONFIRMADO / DISPUTADO / NÃO VERIFICADO na verificação factual.
- Matéria de 400–600 palavras, em parágrafos (sem bullets no corpo), imparcial, com citações `[n]` e seção `## Referências` consistente.

## Cuidados conhecidos (ver CONTEXT.md §8)

- V1/V2 apontam `skills_dir` para `agente/skills` (inexistente).
- V3 grava em `output/V2` por engano.
- `ui/app.py` ajusta `sys.path` depois de importar `registry`, o que pode quebrar o import de `agente`.
- V4 (Research Team com `agno.team.Team`) está no README mas ainda não existe; `time_research` na V3 está definido sem uso.
- Importar módulos de `agente/` instancia agentes e cria diretórios (efeito colateral).

Ao corrigir algum desses itens, atualize também a seção correspondente do `CONTEXT.md`.
