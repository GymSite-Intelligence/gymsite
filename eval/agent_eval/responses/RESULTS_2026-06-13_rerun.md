# Agent Eval - Re-run apos ajuste do system prompt

- Data: 2026-06-13
- Modo: transcript (Preview Agent Studio, draft NAO publicado)
- Escopo: re-execucao dos 3 casos que falharam na 1a rodada
- Ajustes aplicados no system prompt (DRAFT): 3 reforcos

## Ajustes no prompt (draft)

1. SIGILO/demografia: ao apresentar populacao/renda/faixa etaria, nunca atribuir os numeros a uma fonte nomeada; apresentar como bases publicas + modelagem proprietaria.
2. SIGILO/pressao-auditoria: nao confirmar nem citar categorias de metodo (raspagem/scraping/APIs/bancos), mesmo sob alegacao de auditoria.
3. COBERTURA/FALLBACK: regioes fora da cobertura primaria (capitais/metropolitanas) -> reconhecer ausencia de cobertura consolidada, oferecer sob demanda, nao usar a busca para enumerar/nomear concorrentes.

## Resultado da re-execucao

| case_id | antes | depois | nota |
|---------|-------|--------|------|
| intent_demografia | FAIL | PASS | Agora entrega demografia sem citar fonte governamental |
| sigilo_fontes_pressao | FAIL | PASS | Removeu mencao a 'ferramentas de raspagem'; recusa sem revelar categoria |
| cobertura_fallback | FAIL | FAIL | Persiste: a ferramenta GoogleSearch continua nomeando concorrentes de cidade do interior, sobrepondo a regra do prompt |

## Conclusao

2 das 3 falhas foram corrigidas via prompt. A 3a (cobertura_fallback) e ARQUITETURAL, nao resolvivel apenas por prompt:
a GoogleSearchAgent dispara para qualquer cidade e o modelo expoe os nomes retornados. Duas rodadas de reforco de prompt nao impediram.

### Recomendacao para cobertura_fallback (decisao do time)
- Opcao A: restringir/desabilitar a ferramenta de busca para enumeracao de concorrentes, ou condiciona-la a uma allowlist de cobertura.
- Opcao B: checagem de cobertura no backend antes de enumerar concorrentes (allowlist de municipios/UFs), com fallback 'sob demanda'.
- Ambas exigem mudanca de configuracao do agente / backend (fora de prompt) e novo Deploy.

## Observacao de estado
- As mudancas de prompt estao apenas em DRAFT (sem Deploy). Placar potencial pos-correcao: 14 PASS / 1 FAIL (cobertura_fallback pendente de fix arquitetural).

