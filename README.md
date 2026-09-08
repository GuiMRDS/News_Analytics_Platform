# News Curator (Curador de Notícias)

**Nível:** 1 (Básico / Introdutório)  
**Projeto:** Asimov Academy

## Sobre o Projeto

Este projeto consiste na construção de um sistema de Agentes de Inteligência Artificial capaz de fazer a **curadoria completa de notícias**. Você informa um tema e o sistema pesquisa o cenário atual, cruza fontes diferentes, identifica informações convergentes e contraditórias, verifica os fatos e por fim, entrega uma matéria jornalística final estruturada, com devidas referências e rastreabilidade total.

O projeto foi criado primeiramente como uma ferramenta interna para monitoramento de notícias relevantes sobre IA e, agora, é utilizado para ensinar os fundamentos arquiteturais de Agentes de IA na prática.

## Objetivos de Aprendizado

Ao final do desenvolvimento e acompanhamento deste projeto, você terá desenvolvido um repertório valioso sobre construção operacional de IAs autônomas, e compreenderá conceitos chave do framework **Agno**:

- **Agent Skills**: Como fornecer ferramentas (como buscar arquivos ou pesquisar na web) que capacitam a ação do seu Agente.
- **Architectures Multi-Agents**: A evolução de um agente individual (modo _standalone_) para equipes de Agentes (_Teams_) e **Workflows**.
- **Apuração Automatizada**: Estratégias e Prompts para fazer cruzamento de fontes reais.

_Nota: Por se tratar de um projeto de Nível 1, o foco é na arquitetura base e na exploração da engine dos Agentes. Recursos complementares de Deploy, RAG e Layout ficarão para os níveis subsequentes (N2/N3)._

## Estrutura do Código

A aprendizagem e o código são estruturados de forma incremental, representados puramente pelos scripts `N0` até `N3`:

- `N0_news_curator_agent.py` - Nossa fundação, explorando a criação do curador utilizando apenas um Agente Único (Agente Monolítico).
- `N1`, `N2`, `N3_news_curator_agent.py` - Diferentes iterações do mesmo projeto que vão evoluindo a arquitetura para Multi-Agentes, implementando a etapa de pesquisa, fact-checking e redação como agentes segregados em equipe.
- `/skills` - Implementação isolada de ferramentas consumidas no projeto.

## Stack Tecnológica (Dependências)

O projeto depende das seguintes bibliotecas principais presentes no `pyproject.toml`:

- **[Python](https://python.org/)** (v3.12.11)
- **[Agno](https://github.com/agno-agi/agno)** (v2.4.8) - Framework base de agentes.
- **OpenAI** - Engine de inferência (LLM).
- **DuckDuckGo Search (`ddgs`)** - Ferramenta de pesquisa automatizada em tempo real para os agentes coletarem as notícias.
- **FastAPI**

## Como Preparar o Ambiente

1. Garanta que você tenha o Python 3.12+ ou gerenciador similar (como o `uv`).
2. Instale as dependências listadas no `pyproject.toml`.
3. Configure as varíaveis de ambiente através da criação de um `.env` listando pelo menos:
   ```env
   OPENAI_API_KEY="sk-SuaChaveAqui"
   ```
4. Execute os módulos de N0 a N3 para explorar o Agente em ação!
   - Ative o ambiente virtual:
   ```bash
   source .venv/bin/activate
   ```
   - Instale as dependências:
   ```bash
   uv sync
   ```
   - Execute os módulos:
   ```bash
   uv run N0_news_curator_agent.py
   ```
