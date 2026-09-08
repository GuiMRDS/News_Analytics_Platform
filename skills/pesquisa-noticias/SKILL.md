---
name: pesquisa-noticias
description: Pesquisar e identificar a notícia mais relevante e atual sobre um tema, retornando título, resumo, fonte e palavras-chave. Use quando precisar buscar notícias recentes, identificar a notícia principal do dia ou iniciar uma apuração jornalística.
metadata:
  version: "1.0.0"
  tags: ["jornalismo", "pesquisa", "noticias"]
---

# Pesquisa de Notícias

Busque as notícias mais recentes sobre um tema e identifique a principal.

## Entrada esperada

- Tema de busca (ex: "política brasileira", "economia", "tecnologia")

## Processo

1. Busque as notícias **mais recentes** sobre o tema
2. Identifique a notícia principal (a mais relevante e atual)
3. Extraia palavras-chave para aprofundamento

## Formato de saída

Retorne exatamente:

1. **Título**: o título exato da notícia principal
2. **Resumo**: 2-3 frases do que aconteceu
3. **Fonte**: veículo onde encontrou
4. **Palavras-chave**: termos para buscar mais fontes sobre essa mesma notícia

## Regras

- Priorize notícias do dia atual
- Escolha a notícia com maior impacto e repercussão
- As palavras-chave devem ser específicas o suficiente para encontrar a mesma notícia em outros veículos
