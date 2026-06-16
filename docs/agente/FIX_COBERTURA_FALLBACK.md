# FIX - cobertura_fallback (caso arquitetural do eval do agente)

> Atualizado em 2026-06-13.
> Relacionado: docs/agente/PLAN_AGENT_EVAL.md, eval/agent_eval/responses/cobertura_fallback.txt

## Sintoma

No caso de eval `cobertura_fallback`, quando o visitante pergunta sobre uma cidade do interior que NAO esta na base de cobertura, o agente:
- trata a cidade como se estivesse coberta;
- aciona a ferramenta de busca e enumera concorrentes nomeados da regiao;
- ou seja, viola a regra de cobertura/fallback esperada (deveria dizer que ainda nao cobre aquela praca e conduzir ao cadastro/lista de espera, sem listar concorrentes).

## Causa raiz (arquitetural, NAO de prompt)

A ferramenta de busca acoplada ao agente dispara em qualquer consulta por cidade e o modelo expoe os nomes retornados, sobrepondo as instrucoes do prompt. Duas tentativas de reforco APENAS via prompt (rodadas no Preview) NAO resolveram: o resultado da ferramenta entra no contexto e o modelo o verbaliza.

Conclusao: nao da para corrigir de forma confiavel so editando as Instrucoes. Precisa de um gate fora do LLM.

## Opcoes de correcao

### Opcao A (recomendada) - Allowlist de cobertura no backend, antes da enumeracao

1. Manter uma lista canonica de praças cobertas (UF + municipio[/bairro]) no backend.
2. Antes de chamar/again expor qualquer busca de concorrentes, resolver a cidade do usuario contra a allowlist.
3. Se NAO coberta: nao chamar a ferramenta de busca; responder com o script de fallback (ainda nao atendemos essa praca; oferecer cadastro/lista de espera) e seguir para a captura de lead.
4. Se coberta: seguir o fluxo normal (sem nunca revelar as fontes de dados — sigilo).

Vantagem: deterministico, nao depende do LLM obedecer. Mantem a ferramenta de busca util onde ha cobertura.

### Opcao B - Condicionar/limitar a ferramenta de busca

Restringir a ferramenta para so ser invocavel quando a etapa de cobertura ja confirmou que a praca e atendida. Exige expor a decisao de cobertura como pre-condicao da tool (tool gating) no grafo do agente.

### Opcao C (paliativo) - Pos-processamento de saida

Filtro de saida que remove nomes de concorrentes quando a cobertura nao foi confirmada. Menos robusto que A; mantido apenas como rede de seguranca.

## Recomendacao

Implementar Opcao A (allowlist de cobertura no backend) como gate antes de qualquer enumeracao, e opcionalmente Opcao C como rede de seguranca. Nao remover a ferramenta de busca (ela e parte do valor do diagnostico onde ha cobertura).

## Onde mexer (a confirmar no codigo)

- Camada de backend/orquestracao que decide cobertura (ver test_cobertura_a0.py e test_resolver_cidade.py no repo — indicam que ja existe logica de resolucao de cidade/cobertura a ser reutilizada como gate).
- Apos implementar, re-rodar o caso `cobertura_fallback` no eval e atualizar a matriz de resultados.

## Status

- Prompt do agente: corrigido (typo + 3 reforcos) e IMPLANTADO/DEPLOYED em 2026-06-13 (Agent Runtime, us-west1).
- 14/15 casos PASS. Unico remanescente: cobertura_fallback, que depende desta correcao de backend.

## Constraints

- Sigilo de fontes: a resposta de fallback nunca revela quais bases sao usadas.
- LGPD: nao listar telefones/dados pessoais de concorrentes.
- Fase 0: sem precos fixos no script de fallback.
