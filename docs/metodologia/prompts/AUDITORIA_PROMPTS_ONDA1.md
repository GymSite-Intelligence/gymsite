# Auditoria de Prompts — Onda 1 (task #24)

> 2026-07-10. 19 prompts LLM auditados contra o checklist de 6 itens do
> `guia_prompts_pipeline.md`. Itens: (1) instrução na última seção (Gemini) ·
> (2) formato à prova de fence · (3) restrições positivas · (4) abstenção RAG ·
> (5) nenhum número/veredito ao LLM (regra zero) · (6) sem snake_case pra cliente.

## Matriz

| # | Prompt (arquivo:linha) | 1 | 2 | 3 | 4 | 5 | 6 | Gravidade |
|---|---|---|---|---|---|---|---|---|
| 1 | A0 ContextBuilder `a0_context_builder:96` | ⚠️ | ❌ | ⚠️ | ✅ | ✅ | ✅ | média |
| 2 | A3 CompetitorIntel `a3_competitor_intel:27` | ⚠️ | ❌ | ✅ | N/A | ⚠️ | ✅ | média |
| 3 | Classificador de dores `competitor_tools:134` | ⚠️ | ✅ | ✅ | N/A | ✅ | ✅ | baixa |
| 4 | A6 Report principal `a6_report_consolidator:3160` | ⚠️ | ✅ | ⚠️ | N/A | ❌ | ❌ | média |
| 5 | A6 resumo narrado (Claude) `a6:2086` | — | — | ✅ | — | ✅ | — | exemplar |
| 6 | A7 MarketResearch `a7_market_research:26` | ⚠️ | N/A | ✅ | ✅ | ⚠️ | ✅ | baixa |
| 7 | Consultor logado `consultor_engine:398` | ⚠️ | N/A | ✅ | ✅ | ✅ | ✅ | baixa |
| 8–13 | Personas site + assembler `consultor_engine:455-634` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | exemplar |
| 14–19 | agents_site (5 especialistas + roteador) `agents_site/agent.py` | ⚠️ | N/A | ✅ | ✅ | ✅ | ✅ | baixa |

## Achados priorizados

1. **A6 vaza snake_case pro cliente** (`a6:3473` "→ categoria: <categoria_dor>" e
   `:3504` tabela de dores): cliente lê `atendimento_ruim`, `lotacao`. Não existe
   mapa de label amigável pra dores (só `_SERVICO_LABEL` pra serviços).
   → Resolver JUNTO com a task #28 (taxonomia de dores): o mapa código→label
   amigável nasce com a definição auditável de cada dor.
2. **A6 instrui o LLM a CALCULAR scores e veredito** (`a6:3217-3237`) — contra a
   regra zero. Hoje inofensivo (o código sobrescreve determinístico via
   `_ajustar_veredito_no_markdown`), mas o prompt pede exatamente o que a casa
   proíbe. → Onda 2: trocar "calcule" por "copie os valores do bloco de state".
3. **A0 e A3 sem blindagem anti-fence** (`a0:126`, `a3:138`): os dois maiores
   produtores de JSON do pipeline não têm o "SOMENTE o objeto JSON, começando
   por {" — o bug que já mordeu o A3b. → CORRIGIDO nesta onda (baixo risco).
4. **A3 pede número ao LLM** (`a3:97` ticket_medio_estimado por priceLevel;
   `:91` sentimento "composto mentalmente"). → Onda 2; o ticket determinístico
   é a task #26 (mesma raiz).
5. **A6 anexa o state DEPOIS da instrução** (`append_instructions`, `a6:823`) —
   ordem inversa à regra Gemini "contexto grande primeiro, instrução por último".
   → Onda 2 (mexe na montagem do prompt gigante; testar com golden dataset).
6. **Personas duplicadas** em `consultor_engine.py` e `agents_site/agent.py` —
   duas fontes de verdade pra manter em sincronia. → registrar; decidir a canônica.

## O que a Onda 1 corrige (este PR)

- Anti-fence no A0 e no A3 (achado 3): uma linha de instrução em cada, zero risco.

## Onda 2 (registrada, não iniciada)

- Achados 2, 4 (junto do #26), 5 e 6. O 1 vai no #28.
