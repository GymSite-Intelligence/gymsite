# Auditoria de Agentes do Pipeline — CONSTITUTION.md

> Data: 2026-06-18 · Escopo: 13 agentes (A0–A9 + A3a/b/c) + orquestração + repo-level
> Método: 4 subagentes paralelos (code-review) contra C1–C10, fail-closed, evidência `file:linha` + `audit.sh` repo-level.
> Gate (CONSTITUTION §126): ≥7.0 e 0🔴 = APROVADO · 5–7 ou 🔴 mitigado = CONDICIONAL · <5 ou 🔴 sem mitigação = REPROVADO.

## Scorecard consolidado

| Agente | 🔴 | 🟡 | Veredito |
|---|---|---|---|
| A0 ContextBuilder | 1 | 7 | CONDICIONAL |
| A1 GeoScout | 1 | 6 | CONDICIONAL |
| A2 DemoAnalyst | 0 | 3 | CONDICIONAL (mais maduro) |
| A3 CompetitorIntel | 3 | 7 | **NÃO-CONFORME** |
| A3a Search | 1 | 3 | CONDICIONAL |
| A3b Analysis | 1 | 6 | **NÃO-CONFORME** |
| A3c Mapper | 1 | 4 | CONDICIONAL (desligado) |
| A4 Financial | 1 | 3 | CONDICIONAL |
| A5 ContactHunter | 1 | 2 | CONDICIONAL |
| A6 ReportConsolidator | 3 | 5 | CONDICIONAL (frágil) |
| A7 MarketResearch | 5 | 2 | **NÃO-CONFORME (pior)** |
| A8 Validator | 4 | 4 | **NÃO-CONFORME** |
| A9 Positioning | 4 | 4 | **NÃO-CONFORME** |
| Orquestração | 3 | 2 | **REPROVADO** |
| **Repo (audit.sh)** | 2 | 2 | **REPROVADO** (score 7.3, 🔴 travam) |

**Resultado geral: REPROVADO** (deploy bloqueado pela constituição — 🔴 sem mitigação).

## Causas-raiz sistêmicas (ranqueadas por alavancagem)

| # | Furo | Cláusula | Agentes | Fix sistêmico | Destrutivo? |
|---|---|---|---|---|---|
| 1 | `InMemorySessionService` — crash perde run de 10–30min | C6.4 🔴 | TODOS | `DatabaseSessionService` OU snapshot Supabase por `after_agent_callback` | muda prod — confirmar |
| 2 | `after_model_callback` telemetria não hookado (cego pra token/modelo) | C7.2 🔴/🟡 | A0,A1,A3,A6,A7 + bug-chain A9 | factory `build_llm_agent` injeta callback; corrigir `_attach_telemetry` p/ encadear | não |
| 3 | LLM instanciado direto, sem ACL/factory | C5.2 🔴 | A0,A1,A3,A9 | mesma factory `build_llm_agent` | não |
| 4 | Sem `output_key`/schema Pydantic (corrupção downstream) | C6.2 🔴/🟡 | A3,A7 (sem key); A9 sem validação; state dict solto | `PipelineState(BaseModel)` + schema de output por agente | não |
| 5 | Sem SPEC.md por agente (gate CI) | C2.1 🔴/🟡 | TODOS | docs SPEC por agente (ou 1 SPEC_PIPELINE_CORE) | não |
| 6 | Sem testes/evals de agente | C4.3 🟡 | A0,A1,A3,A3b,A3c,A6,A7,A8 | suites por agente + eval no gate | não |
| 7 | Narrativa LLM sem grounding verificável | C8.3 🟡 | A3,A6,A7 (A8/A9 parcial) | exigir âncora-fonte por afirmação + check programático | não |
| 8 | Sem HITL p/ output financeiro | C6.3 🔴 | orquestração | gate humano antes de persistir financeiro/A9 | confirmar (UX) |
| 9 | Sem rate-limit LLM + hard-limit de custo | C9.2/C9.3 🔴 | orquestração | `asyncio.Semaphore` no ParallelAgent + `PIPELINE_MAX_CUSTO_BRL` abort | não |
| 10 | Audit trail mutável (UPDATE, sem hash chain) | C7.1 🔴 | A8,A9 | INSERT append-only + SHA-256 + RLS sem UPDATE/DELETE | confirmar (schema) |
| 11 | Secrets em artefatos commitados (chave Maps em URLs) | C1.1 🔴 | repo | gitignore + scrub history + **rotacionar chave Maps** | DESTRUTIVO — confirmar |

## Pontos fortes (não regredir)

- A2/A4: anti-alucinação via snapshot determinístico (`_persistir_*_no_state`) — A6 lê números da tool, não do LLM.
- A9: override determinístico de veredito (headroom IBGE) + gaps reais.
- A1: `_persistir_macro_no_state` mitiga truncamento do LLM.
- Secrets NO CÓDIGO-FONTE: PASS em todos (leak é só em artefatos JSON).
- Retry 429 + idempotência UPSERT na orquestração: PASS.
