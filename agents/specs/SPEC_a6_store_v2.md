# SPEC — A6 ReportConsolidator store / latência v2

---
id: spec-a6-store-v2
agente: ReportConsolidator
versao: 2.0
data: 2026-07-16
fonte: agents/a6_report_consolidator.py
diagrama: agents/specs/SPEC_a6_store_v2.mmd · agents/a6_report_consolidator.mmd
5whys: tools/a6_report_consolidator_5whys.mmd
---

## 1. Forma

**Único LLM restante no miolo** (Flash + thinking 8192). Tools: `obter_data_atual`, `bairros_alternativos_inteligentes` (também no precompute).

Callbacks:
1. `before_agent` → precompute bairros + entrantes CNPJ + obras CNO (+ telemetry)
2. `before_model` → injeta seções markdown pré-computadas no system prompt
3. `after_agent` → JSON canônico + alinhamento MD + Supabase

Retest `6bb90ff7`: **369s** — #2 wall após A3a.

## 2. Granularidade (tempo)

| Bloco | Tipo | Store histórico? | Custo típico |
|---|---|---|---|
| `bairros_alternativos_inteligentes` | **live** Places/OSM/CNPJ × N bairros | **não** (por bairro alt) | **alto** se Maps cold |
| entrantes CNPJ 90d | Supabase RFB | **sim** | baixo |
| obras CNO | FS `CNO_DATA_DIR` | semi | médio I/O |
| demografia_bairro / IPECE / zoneamento / fluxo / anéis / cross-check | tools det. | misto | médio (Nominatim+calcs) |
| LLM Flash markdown | Gemini | — | **alto** tokens + thinking |
| after: write JSON + SB | I/O | — | baixo |

## 3. O que NÃO é store de “histórico de relatório”

A6 **consome** stores A0/A3a; não substitui. Persistência = `metrics/relatorios` + Supabase = **output** do run, não cache de input.

## 4. Act-on (prioridade)

| # | Ação | Efeito |
|---|---|---|
| 1 | Cache Places por `(bairro_alt, cidade)` TTL (igual A3a maps) | corta precompute Maps×N |
| 2 | Skip `buscar_academias` se `BAIRROS_ALTERNATIVOS` já tem count de run recente / parque CNPJ | menos API |
| 3 | Thinking budget ↓ (4096→2048) + medir qualidade golden | corta ~s LLM |
| 4 | Slim state já feito (`_slim_concorrente`); manter | — |
| 5 | Stepper: `etapa_atual` paralelo — UX (não tempo A6) | ver auditoria conformidade |

## 5. Relação A3a

A6 369s vs A3a 1844s — otimizar A3a primeiro. A6 Act-on 1–2 só se A3a já sob store.
