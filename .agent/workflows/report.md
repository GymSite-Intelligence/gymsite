---
description: Generate viability report via A0–A9 pipeline (prod enqueue or local). SearchAPI-primário; aluguel = MRLR.
---

# Workflow: /report

> **Skill:** `gymsite-pipeline` · `gymsite-reporting`.
> **Regras:** [conferencia-fontes-pipeline.md](../rules/conferencia-fontes-pipeline.md) · [pipeline-fontes-deterministicas.md](../rules/pipeline-fontes-deterministicas.md) · P-000 §5–§6 · [PIPELINE_AGENTES.md](../../docs/arquitetura/PIPELINE_AGENTES.md).
> **Não confundir:** `/audit` · `/prospect`. Aluguel OPEX = **MRLR** (A4 Tier 0) — nunca listing/`rent_sqm`/A7.

## Prerequisites

- Prod: API `https://api.getgymsite.com.br` + worker com mesma imagem (`/deploy`)
- Env: `SEARCHAPI_KEY`, Supabase service, Vertex/Gemini conforme A0
- Inputs: cidade, UF, bairro, `area_m2_min/max` (ou preset), `tipo_negocio`

## Pipeline (mapa rápido)

| Agente | Papel | Fonte canônica |
|---|---|---|
| A0 ContextBuilder | briefing | bundle/CKAN + research; CNPJ override det. |
| A1 GeoScout | candidatos | SearchAPI listing + geocode |
| A2 DemoAnalyst | demografia | IBGE |
| A3a CompetitorSearch | concorrentes+reviews+pico | SearchAPI Maps/place; Places = fallback |
| A3b CompetitorAnalysis | gaps/saturação | state A3a (det.) |
| A4 FinancialEstimator | 3 cenários | **MRLR** aluguel |
| A5 ContactHunter | decisor | CNPJ/contato |
| A6 ReportConsolidator | markdown/PDF narrado | tools + guardrail |
| A7 | chat/grounding lateral | **fora** do path aluguel/concorrência |
| A9 PositioningStrategist | ERRC / veredito oceano | det. + narrador |

## Steps

1. **Collect inputs**
   - cidade, uf, bairro, area min/max, tamanho_preset, publico/genero, tipo_negocio

2. **Enqueue (prod — preferido)**
   ```powershell
   # Smoke Cocó (ou POST manual)
   .\.venv\Scripts\python.exe scripts\smoke_adr006_coco.py
   ```
   Ou `POST /api/relatorios` → poll `/api/relatorios/{id}/status` até `done`/`failed`.
   Pipeline **roda no worker** — se `etapa_atual` travada + Redis `processing` órfão, ver `/debug`.

3. **Local (dev only)**
   - Runner ADK + stub `relatorios` — não substitui validação prod worker
   - Python: `.venv\Scripts\python.exe`

4. **Validate fontes (não só “PDF existe”)**
   - `fonte_aluguel` contém MRLR / IBAPE
   - Ledger: listing = `searchapi_*`; Places só com fallback logado
   - Demografia: `populacao_fonte` / IBGE
   - Carimbo P-010 em números exibidos (PDF/UI)

5. **Validate artefato**
   - `status=done`, `tempo_execucao_segundos`, etapas A0→A9 em `etapas_concluidas`
   - PDF/URL se gerado; size > 10KB se local `artifacts/`

## Output

- UUID `relatorios.id` + outputs em `gymsite.relatorio_outputs` / `competidores`
- PDF conforme writer A6/A9

## Anti-padrões

- ❌ Tratar Places como primário de concorrentes
- ❌ Citar `bundle.aluguel_portais` / SearchAPI rent como OPEX
- ❌ Validar só “PDF > 10KB” sem checar `fonte_aluguel`
