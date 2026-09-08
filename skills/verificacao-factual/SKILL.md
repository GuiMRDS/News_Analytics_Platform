---
name: verificacao-factual
description: Verificar fatos de um dossiê jornalístico com análise crítica exaustiva, cruzando fontes, resolvendo contradições, preenchendo lacunas e classificando cada fato por nível de confiança. Use quando precisar fact-check, verificar fatos, resolver contradições entre fontes ou classificar confiabilidade de informações.
metadata:
  version: "1.0.0"
  tags: ["jornalismo", "fact-check", "verificacao"]
---

# Verificação Factual

Análise crítica exaustiva de um dossiê de evidências jornalísticas.

## Entrada esperada

- Dossiê de evidências (produzido pela skill apuracao-fontes)

## Processo

Execute TODOS os passos em sequência, sem pedir permissão:

### Passo 1 — Cruzamento inicial
Compare cada fato entre todas as fontes. Classifique como:
- **CONFIRMADO**: 2+ fontes concordam
- **DISPUTADO**: fontes divergem
- **NÃO VERIFICADO**: apenas 1 fonte

### Passo 2 — Resolução de contradições
Para cada fato DISPUTADO:
1. Busque fonte oficial/primária (governo, nota oficial, Reuters/AP/AFP)
2. Busque dados brutos (relatórios, documentos, balanços)
3. Se encontrou nova informação, reavalie
4. Se persiste, busque com termos diferentes ou fontes internacionais
5. Após 3+ tentativas sem resolver → classifique como "não resolvida" com razão provável

### Passo 3 — Preenchimento de lacunas
Para cada lacuna:
1. Busca específica sobre o ponto em aberto
2. Tente fontes alternativas (sites oficiais, agências internacionais)
3. Reformule a pesquisa com termos diferentes
4. Após 2+ tentativas → marque "pendente — esgotadas as fontes disponíveis"

### Passo 4 — Verificação de fatos únicos
Para cada fato de fonte única:
1. Busque em pelo menos 2 fontes adicionais
2. Se confirmar → promova para CONFIRMADO
3. Se contradizer → mova para DISPUTADO e repita Passo 2
4. Se não encontrar → mantenha NÃO VERIFICADO com alerta

### Passo 5 — Consistência final
Revise datas, nomes, valores e citações de todo o relatório.

## Formato de saída

```
## FATOS CONFIRMADOS
Fatos com alto grau de confiança + fontes que confirmam.

## FATOS DISPUTADOS RESOLVIDOS
Versão original das fontes → o que encontrou → veredito final.

## FATOS DISPUTADOS NÃO RESOLVIDOS
O que cada fonte diz, buscas feitas, razão provável, recomendação ao redator.

## FATOS NÃO VERIFICADOS
Informações de fonte única não corroboradas + buscas tentadas.

## LACUNAS RESOLVIDAS
Lacunas preenchidas + fonte usada.

## LACUNAS PENDENTES
O que permanece sem resposta + buscas tentadas.

## ALERTA AO REDATOR
- O que pode ser AFIRMADO com segurança
- O que DEVE ter ressalva (e qual)
- O que NÃO DEVE ser publicado sem confirmação adicional
- Nível de confiança geral (alto/médio/baixo)
```

## Regras

- Execute IMEDIATAMENTE, sem pedir permissão ou fazer perguntas
- Faça todas as buscas necessárias antes de classificar como "não resolvido"
- Explique a razão provável de cada contradição não resolvida
- Seja específico: cite valores, nomes e datas exatos
