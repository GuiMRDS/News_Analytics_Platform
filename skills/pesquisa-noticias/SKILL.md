---
name: pesquisa-noticias
description: Pesquisar e identificar a notícia mais relevante e atual sobre um tema, com prioridade para mercado financeiro e investimentos (ações, renda fixa, renda variável, fundos, câmbio, juros, cripto, economia), retornando título, resumo, fonte, ativos envolvidos e palavras-chave. Use para iniciar a cobertura de qualquer tema.
metadata:
  version: "2.0.0"
  tags: ["jornalismo", "pesquisa", "noticias", "mercado-financeiro", "investimentos"]
---

# Pesquisa de Notícias (foco: mercado financeiro)

Encontre a notícia principal e mais recente sobre o tema.

## Entrada
Tema ou pergunta (ex.: "Por que PETR4 caiu hoje?", "Copom e a Selic", "fundos imobiliários", "eleições").

## Processo
1. Busque notícias **recentes** sobre o tema (prefira a ferramenta de notícias).
2. Se o tema for financeiro, priorize: Valor Econômico, InfoMoney, Bloomberg Línea, Reuters, Estadão E-Investidor, Exame Invest, Money Times, CNN Brasil Business; e fontes oficiais (B3, CVM, Banco Central, Tesouro Nacional, RI das empresas).
3. Temas não financeiros também são aceitos: use os grandes veículos gerais.
4. Escolha a notícia de maior impacto e atualidade.

## Formato de saída
1. **Título**: título exato da notícia principal
2. **Resumo**: 2-3 frases
3. **Fonte**: veículo e URL
4. **Ativos e indicadores envolvidos**: tickers (ex.: PETR4, VALE3, MXRF11), índices, taxas (Selic, CDI, IPCA), moedas. Escreva "nenhum" se não houver
5. **Palavras-chave**: termos específicos para achar a mesma notícia em outros veículos

## Regras
- No máximo 3 buscas; seja objetivo.
- Nunca invente tickers, números ou datas.
