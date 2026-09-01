# SPEC — A4 FinancialEstimator (+ A4bak) store / latência v2

---
id: spec-a4-store-v2
agente: FinancialEstimator
versao: 2.0
data: 2026-07-16
fonte_prod: agents/a4_financial_estimator.py (BaseAgent)
bak: LLM Agent histórico no paste / commits antigos — NÃO no grafo atual
diagrama: agents/specs/SPEC_a4_store_v2.mmd · agents/a4_financial_estimator.mmd
---

## 1. Forma prod (atual)

**BaseAgent** — `await analise_financeira_a4_completo` + `_justificativa_det` template.  
State: `analise_financeira_pronto` + `analise_financeira`.

Retest `6bb90ff7`: **1,7s** — aluguel MRLR hit / sem portais longos.

## 2. Granularidade macro (`financial_tools.analise_financeira_a4_completo`)

| Passo | Fonte | Store? | Live? |
|---|---|---|---|
| Aluguel Tier 0 | `aluguel_mrlr` / espelhos `renda_bairro`+`municipio_pib` | **sim** (BQ/SB) | lookup |
| Tier 1 portais | SearchAPI/listing cascata | **não** decisão | só se MRLR miss |
| Tier 2 grounding | Gemini search | **não** | miss |
| CAPEX / cenários / score | `param()` + fórmulas | params tabela | CPU |
| Justificativa | template gênero | — | CPU |

**Regra canônica:** aluguel viabilidade = MRLR, nunca listing, nunca A7.

## 3. A4bak (legado LLM)

Paste do usuário = `Agent(gemini-3.6-flash)` ecoando macro + instruction gigante.  
**Fora do `agent.py` atual.** Manter só como referência anti-regressão:

| | Prod BaseAgent | BAK LLM |
|---|---|---|
| Tokens | 0 | alto |
| `justificativa` | template | LLM (alucina/drop) |
| Snapshot | `analise_financeira_pronto` | echo frágil |

Não reintroduzir BAK no grafo.

## 4. Act-on

Nenhum pra wall-clock. Garantir worker tem espelhos MRLR; se Tier0 miss → A4 sobe (monitorar `fonte_aluguel`).
