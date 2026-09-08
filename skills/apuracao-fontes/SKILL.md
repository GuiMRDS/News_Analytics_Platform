---
name: apuracao-fontes
description: Apurar e cruzar múltiplas fontes jornalísticas sobre uma notícia, montando um dossiê estruturado com evidências, linha do tempo, consensos, contradições e lacunas. Use quando precisar investigar fontes, cruzar informações de veículos diferentes ou montar dossiê de evidências sobre uma notícia.
metadata:
  version: "1.0.0"
  tags: ["jornalismo", "apuracao", "fontes", "dossie"]
---

# Apuração de Fontes Jornalísticas

Workflow para investigar uma notícia em múltiplas fontes e produzir um dossiê estruturado de evidências.

## Quando usar

- Recebeu uma notícia e precisa verificar em outras fontes
- Precisa montar um dossiê de evidências sobre um assunto
- Quer cruzar informações de diferentes veículos

## Entrada esperada

- Título ou resumo da notícia a ser apurada
- Palavras-chave para busca (opcional — se não fornecidas, extraia do título)

## Processo

1. **Buscar fontes**: use as palavras-chave para buscar a mesma notícia em diferentes veículos (mínimo 3, ideal 5)
2. **Extrair fatos**: para cada fonte, registre dados, números, nomes e citações diretas
3. **Cruzar informações**: identifique consensos, contradições e exclusividades
4. **Montar dossiê**: produza o documento estruturado no formato abaixo

## Formato de saída

Produza o dossiê exatamente nesta estrutura:

```
## FONTES COLETADAS

Para cada fonte encontrada:
- **Veículo** | URL | Data/hora de publicação
- Fatos reportados (dados, números, nomes, citações diretas)
- Informação exclusiva dessa fonte (o que só ela traz)

## LINHA DO TEMPO

Eventos em ordem cronológica com a fonte entre colchetes.
Ex: "10h — Governo anuncia medida X [Folha] [Reuters]"

## PONTOS DE CONSENSO

Fatos que TODAS ou a maioria das fontes confirmam.

## CONTRADIÇÕES E DIVERGÊNCIAS

Dados que diferem entre fontes. Seja específico:
- Ex: "Folha diz R$ 2,5 bi; Estadão diz R$ 2,8 bi; Reuters diz USD 500 mi"
- Ex: "G1 afirma que a decisão foi unânime; Valor diz que houve 2 votos contrários"

## LACUNAS

O que nenhuma fonte esclareceu ou o que falta confirmar.
```

## Regras

- Mínimo de **3 fontes**, ideal **5 ou mais**
- Priorize veículos de credibilidade reconhecida (Reuters, AP, AFP, grandes jornais)
- Nunca invente dados — registre apenas o que as fontes efetivamente publicaram
- Seja específico nas contradições: cite valores, nomes e datas exatos de cada fonte
- Inclua a URL de cada fonte sempre que disponível
