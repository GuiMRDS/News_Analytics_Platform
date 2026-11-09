---
name: apuracao-fontes
description: Apurar e cruzar múltiplas fontes sobre uma notícia, com ênfase em mercado financeiro (cotações, resultados, fatos relevantes, decisões de juros), montando um dossiê com fontes, linha do tempo, números-chave, consensos, contradições e lacunas. Use para investigar e cruzar fontes de uma notícia.
metadata:
  version: "2.0.0"
  tags: ["jornalismo", "apuracao", "fontes", "dossie", "mercado-financeiro"]
---

# Apuração de Fontes

Investigue a notícia em múltiplas fontes e produza um dossiê de evidências.

## Entrada
Título/resumo da notícia, ativos envolvidos e palavras-chave.

## Processo
1. Busque a mesma notícia em veículos diferentes (mínimo 3, ideal 5), em português e inglês.
2. Em temas financeiros, procure também a fonte primária: fato relevante/comunicado (CVM, RI da empresa), ata/comunicado do Copom (Banco Central), dados da B3 ou do Tesouro.
3. Registre números exatos: preços, variações %, lucros, receitas, taxas, prazos, datas.
4. Cruze as informações: consensos, contradições, exclusividades.

## Formato de saída
```
## FONTES COLETADAS
- **Nome do Veículo**: Título da matéria (URL completa) — data
  Fatos e números reportados por essa fonte

## NÚMEROS-CHAVE
Valores relevantes com a fonte entre colchetes. Ex.: "Lucro líquido de R$ 20,1 bi no 3T [Valor]"

## LINHA DO TEMPO
Eventos em ordem cronológica com a fonte.

## PONTOS DE CONSENSO
## CONTRADIÇÕES E DIVERGÊNCIAS
Seja específico: "InfoMoney diz alta de 3,2%; Reuters diz 2,9%".
## LACUNAS
```

## Regras
- O nome do veículo vai SEMPRE em **negrito** com a URL completa (formato acima).
- Priorize veículos especializados e fontes oficiais.
- Nunca invente dados; registre só o que as fontes publicaram.
- No máximo 4 buscas.
