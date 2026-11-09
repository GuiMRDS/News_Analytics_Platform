---
name: verificacao-factual
description: Verificar fatos de um dossiê jornalístico, com atenção especial a números do mercado financeiro (cotações, variações, taxas, resultados), cruzando fontes, resolvendo contradições e classificando cada fato por nível de confiança. Use para fact-check e para resolver contradições entre fontes.
metadata:
  version: "2.0.0"
  tags: ["jornalismo", "fact-check", "verificacao", "mercado-financeiro"]
---

# Verificação Factual

Análise crítica do dossiê. Execute imediatamente, sem pedir permissão.

## Processo
1. **Classifique cada fato**: CONFIRMADO (2+ fontes concordam), DISPUTADO (fontes divergem) ou NÃO VERIFICADO (1 fonte).
2. **Resolva contradições** buscando a fonte primária (comunicado oficial, CVM, Banco Central, B3, RI da empresa, Reuters/AP/AFP).
3. **Números de mercado**: se tiver ferramentas de dados de mercado, confira cotações, variações e indicadores (Selic, CDI, IPCA, dólar) e registre o valor oficial com data. Cotações mudam ao longo do dia: diferenças pequenas entre fontes podem ser de horário, não erro.
4. **Revise** datas, nomes, tickers, valores e citações.

## Formato de saída
```
## FATOS CONFIRMADOS
## FATOS DISPUTADOS
O que cada fonte diz → veredito (resolvido / não resolvido e razão provável)
## FATOS NÃO VERIFICADOS
## DADOS DE MERCADO CONFERIDOS
Valor oficial, fonte e data de referência
## FONTES
- **Nome do Veículo**: Título (URL), preservando todas as fontes do dossiê
## ALERTA AO REDATOR
- O que pode ser afirmado com segurança
- O que deve ter ressalva
- O que não deve ser publicado
- Nível de confiança geral (alto/médio/baixo)
```

## Regras
- Seja específico: valores, nomes e datas exatos.
- No máximo 4 buscas.
