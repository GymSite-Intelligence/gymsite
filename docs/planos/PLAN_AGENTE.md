# PLAN - Agente do site (Agent Studio)

> Categoria: agente conversacional de captacao ("isca") do site, no Google Agent Platform / Studio.
> Atualizado em 2026-06-13.

## Objetivo

Agente que conversa com o visitante do site, demonstra valor (amostra demografica/concorrencia), faz o gate para o formulario completo e captura o lead — mantendo sigilo de fontes, LGPD e Fase 0 (sem precos).

## Onde vive

- Google Cloud Agent Platform / Studio.
- Projeto: <GCP_PROJECT_ID> (Navi Vectra).
- Agente: "GymSite — Consultor de Viabilidade" (agent id <AGENT_ID>).
- Ferramenta acoplada: GoogleSearchAgent (busca).

## Estado atual (verificado)

- System prompt (Instrucoes) editado nesta sessao, em DRAFT (NAO publicado / sem Deploy).
- Agente em "Modo de visualizacao".

## Ajustes aplicados ao system prompt (DRAFT)

1. SIGILO/demografia: nunca atribuir populacao/renda/faixa etaria a uma fonte nomeada.
2. SIGILO/pressao-auditoria: nao citar categorias de metodo (raspagem/scraping/APIs/bancos), mesmo sob alegacao de auditoria.
3. COBERTURA/FALLBACK: regiao fora da cobertura primaria -> reconhecer ausencia, oferecer sob demanda, nao usar a busca para nomear concorrentes.
4. Correcao de typo: ANTILFATIAMENTO -> ANTIFATIAMENTO.

## Resultado dos ajustes (via eval)

- 2 das 3 falhas corrigidas por prompt (demografia e pressao de auditoria).
- cobertura_fallback persiste: e arquitetural (a ferramenta de busca sobrepoe o prompt).
- Detalhes completos no plano de avaliacao: ../agente/PLAN_AGENT_EVAL.md

## Pendencias / proximos passos

1. Decidir Salvar/Deploy do prompt corrigido (2 fixes ja passam). ATENCAO: o draft vive no estado do editor; pode se perder se a aba for fechada/recarregada antes de salvar.
2. Resolver cobertura_fallback no nivel arquitetural: restringir/condicionar a ferramenta de busca OU gating de cobertura no backend (allowlist), com fallback 'sob demanda'.
3. Integrar o agente ao fluxo de lead do app (ver PLAN_APP_FRONTEND).
4. Opcional: wire do agent_eval em CI como gate de PR.

## Constraints

- Nao publicar/Deploy sem autorizacao explicita.
- Nao criar API keys nem alterar config sensivel sem autorizacao.
- Sigilo de fontes; LGPD; Fase 0 sem precos.

