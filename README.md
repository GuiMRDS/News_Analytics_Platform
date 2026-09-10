# 📰 Curadoria de Notícias com IA

Sistema de curadoria jornalística baseado em agentes de IA utilizando **Agno**, **Groq**, **Workflows**, **Skills Customizadas** e **Arquitetura Multiagente**.

O projeto simula o fluxo de trabalho de uma redação moderna, permitindo que agentes especializados pesquisem, apurem, validem e redijam matérias jornalísticas automaticamente.

---

## 🚀 Objetivo

Construir uma plataforma de curadoria de notícias utilizando Inteligência Artificial para:

- Pesquisar informações em múltiplas fontes
- Realizar apuração jornalística
- Executar verificação factual
- Gerar matérias estruturadas
- Evoluir diferentes arquiteturas de agentes (V1, V2, V3, V4...)
- Comparar estratégias de orquestração com Agno

---

# 🏗️ Arquitetura

O projeto evolui através de versões, cada uma explorando diferentes abordagens de engenharia de agentes.

## V1 — Agente Monolítico

Um único agente responsável por executar todas as etapas da curadoria.

```text
Tema
 ↓
Agente Jornalista
 ↓
Matéria Final
```

---

## V2 — Workflow Sequencial

Separação das responsabilidades em agentes especializados.

```text
Tema
 ↓
Pesquisador
 ↓
Apurador
 ↓
Verificador
 ↓
Redator
 ↓
Matéria Final
```

---

## V3 — Workflow com Controle de Qualidade

Introdução de validações e melhorias no processo de apuração.

```text
Tema
 ↓
Pesquisa
 ↓
Apuração
 ↓
Validação
 ↓
Redação
 ↓
Matéria Final
```

---

## V4 — Multi-Agent Research Pipeline

Versão atual.

Implementa:

- Equipe de pesquisa
- Loop de apuração
- Validação de quantidade mínima de fontes
- Verificação factual
- Redação automatizada
- Exportação Markdown

```text
Tema
 ↓
Research Team
 ↓
Apuração
 ↓
Validação de Fontes
 ↓
Fact Checking
 ↓
Redação
 ↓
Markdown
```

---

# 🤖 Agentes Especializados

## 🔍 Pesquisador

Responsável por:

- Buscar informações relevantes
- Identificar notícias recentes
- Coletar contexto inicial

---

## 📚 Apurador

Responsável por:

- Encontrar múltiplas fontes
- Comparar informações
- Identificar divergências
- Garantir diversidade de veículos

---

## ✅ Verificador Factual

Responsável por:

- Confirmar informações
- Validar fatos
- Detectar inconsistências
- Avaliar confiabilidade das fontes

---

## ✍️ Redator

Responsável por:

- Produzir a matéria final
- Organizar referências
- Estruturar o texto jornalístico
- Gerar arquivo Markdown

---

# 🔄 Workflow Inteligente

A V4 utiliza recursos avançados de Workflow do Agno.

## Loop de Apuração

O sistema repete automaticamente a etapa de apuração até atingir um número mínimo de fontes confiáveis.

```text
Apuração
   │
   ▼
Quantidade mínima atingida?
   │
 ┌─┴─┐
 │   │
Não Sim
 │   │
 ▼   ▼
Repete Continua
```

Essa estratégia aumenta a qualidade das matérias produzidas.

---

# 🧩 Skills

As responsabilidades foram desacopladas em Skills reutilizáveis.

```text
skills/
├── pesquisa-noticias/
├── apuracao-fontes/
├── verificacao-factual/
└── redacao-jornalistica/
```

Isso permite:

- Reutilização
- Facilidade de manutenção
- Evolução independente de cada etapa

---

# 🛠️ Tecnologias

### Linguagem

- Python 3.13+

### Framework de Agentes

- Agno

### Modelo de IA

- Groq
- GPT OSS 20B

### Busca

- DuckDuckGo Search

### Orquestração

- Agno Workflow
- Step
- Loop
- Team

### Persistência

- Markdown

### Interface

- Streamlit

---

# 📂 Estrutura do Projeto

```text
Curadoria_Noticias/
│
├── agente/
│   ├── agente_curador.py
│   ├── agente_curador_v2.py
│   ├── agente_curador_v3.py
│   └── agente_curador_v4.py
│
├── skills/
│   ├── pesquisa-noticias/
│   ├── apuracao-fontes/
│   ├── verificacao-factual/
│   └── redacao-jornalistica/
│
├── output/
│
├── ui/
│   ├── app.py
│   ├── registry.py
│   └── components/
│
└── README.md
```

---

# ⚙️ Instalação

Clone o projeto:

```bash
git clone https://github.com/GuiMRDS/Curadoria_Noticias.git
```

Entre na pasta:

```bash
cd Curadoria_Noticias
```

Instale as dependências:

```bash
uv sync
```

ou

```bash
pip install -r requirements.txt
```

---

# 🔑 Configuração

Crie um arquivo `.env`:

```env
GROQ_API_KEY=sua_chave
```

Obtenha sua chave em:

https://console.groq.com

---

# ▶️ Executando

## Workflow

```bash
python agente/agente_curador_v4.py
```

Exemplo:

```python
news_curator_workflow.print_response(
    "Quem é Gustavo Guanabara?",
    stream=True
)
```

---

## Interface Streamlit

```bash
streamlit run ui/app.py
```

---

# 💡 Conceitos Explorados

Este projeto explora conceitos modernos de IA e Engenharia de Software:

- Multi-Agent Systems
- Agent Engineering
- Workflow Orchestration
- Fact Checking Assistido por IA
- Prompt Engineering
- Tool Calling
- Modularização por Skills
- Arquiteturas Escaláveis de Agentes

---

# 👨‍💻 Autor

**Guilherme Marinho**

Software Engineer | Python | IA & Automação | C# .NET | Cloud | Cybersecurity

GitHub:  
https://github.com/GuiMRDS

LinkedIn:  
https://www.linkedin.com/in/guilhermemrds/

---

⭐ Se este projeto foi útil para você, considere deixar uma estrela no repositório.
