---
name: analise-mercado
description: Analisar o impacto de uma notícia no mercado financeiro usando dados reais (cotações da B3 e globais, Selic, CDI, IPCA, dólar), explicando efeitos em renda variável, renda fixa, fundos, câmbio e cripto em linguagem acessível ao investidor. Use depois da verificação factual e antes da redação.
metadata:
  version: "1.0.0"
  tags: ["mercado-financeiro", "investimentos", "analise", "acoes", "renda-fixa", "fundos"]
---

# Análise de Mercado para Investidores

Transforme a notícia verificada em contexto de mercado, com dados reais.

## Processo
1. Identifique os ativos e indicadores envolvidos (tickers, índices, taxas, moedas).
2. Use as ferramentas de mercado (no máximo 4 chamadas):
   - `cotacao_ativo` para cada ticker relevante (até 3);
   - `indicadores_economicos` se o tema envolver juros, inflação, renda fixa ou câmbio;
   - `simular_investimento_renda_fixa` apenas se ajudar a explicar o impacto de juros (ex.: R$ 10.000 por 12 meses a 100% do CDI).
3. Explique o impacto provável por classe de ativo, com cautela ("tende a", "pode"), sem recomendar compra ou venda.

## Formato de saída
```
## PAINEL DE MERCADO
Ativo/indicador | valor | variação | data/fonte

## IMPACTO POR CLASSE DE ATIVO
- Renda variável (ações, ETFs, BDRs):
- Renda fixa (Tesouro, CDB, LCI/LCA, debêntures):
- Fundos (FIIs, multimercado, renda fixa):
- Câmbio e cripto:
(inclua só as classes relevantes para a notícia)

## RISCOS E O QUE ACOMPANHAR
Próximos eventos (Copom, balanços, payroll, dados de inflação), riscos e sinais a observar.

## GLOSSÁRIO
2-5 termos técnicos da notícia explicados em uma frase cada.
```

## Regras
- Use apenas números retornados pelas ferramentas ou presentes no relatório, sempre com data e fonte.
- Se uma ferramenta falhar, diga que o dado está indisponível; nunca estime cotações.
- Sem recomendação de investimento.
- Se o tema não tiver relação com mercado, responda apenas: "Sem impacto direto identificado no mercado financeiro."
