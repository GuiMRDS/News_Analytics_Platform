---
name: redacao-jornalistica
description: Redigir matéria jornalística profissional a partir de um relatório de verificação factual, com título original, lide, corpo em pirâmide invertida e contexto. Use quando precisar escrever notícia, redigir matéria, produzir texto jornalístico ou transformar dossiê em notícia publicável.
metadata:
  version: "1.0.0"
  tags: ["jornalismo", "redacao", "materia"]
---

# Redação de Matéria Jornalística

Escreva a notícia como se fosse publicada agora em um veículo de imprensa real.

## Entrada esperada

- Relatório de verificação factual (produzido pela skill verificacao-factual)

## Estrutura da matéria

### Título
Crie um NOVO título jornalístico — não copie das fontes. Factual, forte e informativo.

Exemplos de bons títulos:
- "Governo federal anuncia corte de R$ 15 bi no Orçamento de 2026"
- "STF forma maioria e valida marco temporal para terras indígenas"
- "Dólar recua para R$ 5,12 após sinalização do Fed sobre juros"

### Lide (1º parágrafo)
Responda: O QUÊ, QUEM, QUANDO, ONDE e POR QUÊ. Deve funcionar sozinho.

### Corpo (3-5 parágrafos)
- Pirâmide invertida (fatos mais importantes primeiro)
- Atribuição natural: "Segundo o Ministério...", "De acordo com dados do IBGE..."
- Divergências de forma natural: "Enquanto a Folha aponta R$ 2,5 bi [1], o Estadão estima R$ 2,8 bi [2]"
- Fatos não verificados com ressalvas: "a informação ainda não foi confirmada oficialmente"
- Números, datas, nomes e dados concretos
- Citações diretas entre aspas quando disponíveis
- **CITAÇÕES OBRIGATÓRIAS**: Sempre que mencionar um dado, fato ou citação de uma fonte, insira a referência numérica correspondente entre colchetes — ex: [1], [2], [3]. Cada número deve corresponder a uma entrada na seção "Referências" no final do texto.

### Contexto (1 parágrafo)
Cenário mais amplo, o que veio antes, por que importa.

### Referências
No final da matéria, inclua uma seção `## Referências` com a lista numerada de TODAS as fontes citadas no texto, no formato:

```
## Referências

[1] Nome do Veículo — Título da matéria. URL
[2] Nome do Veículo — Título da matéria. URL
[3] Nome do Veículo — Título da matéria. URL
```

- Use a mesma numeração usada nas citações [1], [2] etc. no corpo do texto
- Inclua a URL completa de cada fonte (extraída do dossiê de apuração/verificação)
- Se o título exato não estiver disponível, use uma descrição breve do conteúdo
- TODAS as fontes mencionadas no corpo DEVEM aparecer na lista de referências
- TODAS as entradas na lista de referências DEVEM ser citadas pelo menos uma vez no corpo

## Regras inegociáveis

- Português brasileiro fluente, tom jornalístico profissional
- Sério, direto, imparcial — sem opinião, sem adjetivos desnecessários
- SEMPRE use citações numéricas [1], [2], [3] no corpo para indicar a fonte de cada informação
- SEMPRE inclua a seção "Referências" no final com URLs completas
- NUNCA use bullet points no corpo — escreva em PARÁGRAFOS corridos
- NUNCA invente dados, nomes ou citações
- Extensão: 400-600 palavras (sem contar a seção de referências)
- Deve parecer que saiu de uma redação de verdade, NÃO de uma IA
