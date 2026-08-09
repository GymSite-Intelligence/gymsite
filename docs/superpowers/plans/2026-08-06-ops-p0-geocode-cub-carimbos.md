> **Wave 2 status (2026-08-06):** Tasks 7–8 done. Gate CLI acusa MS/PI stale no golden atual (esperado). CI roda só unit tests até PR atualizar CUB.
> **Wave 1 status (2026-08-06):** Tasks 1–6 implemented; PDF copy/pirâmide aprovados Marcelo.

# Ops P0 (geocode hard gate + CUB PR + carimbos + ingest BR) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hard-fail blind market bundles when geocode misses; honest demografia/CNPJ carimbos on PDF+front; monthly CUB PR gate; VPS-BR RFB/CNO ingest via Supabase cron + mirror health — without new GCP or OSM migration.

**Architecture:** Three waves. W1 changes batch builder + PDF/front copy only. W2 adds pure CUB golden validators + runbook (no scraper). W3 reuses `gymsite.cron_http_targets` → HTTP → VPS Brasil endpoint that runs existing loaders; separate health checks for MRLR mirrors.

**Tech Stack:** Python 3.11+, pytest, FastAPI `internal_cron`, Supabase pg_cron/pg_net, React/TS front, Jinja PDF.

**Spec:** `docs/superpowers/specs/2026-08-06-ops-p0-geocode-cub-carimbos-design.md`

## Global Constraints

- Hard gate geocode: sem `lat`/`lng` com bairro informado → **não** `save_market_bundle`; exit ≠ 0 / exceção tipada
- OSM Nominatim **primário** = fora (VEC-378); fallback Nominatim só se `MAPS_FALLBACK_ENABLED` já ligado
- CUB: PR + gate; **zero** scrape SindusCon
- Carimbos: PDF + front alinhados; **sem** lib compartilhada v1
- Cron = despertador HTTP; executor = **VPS Brasil** (não Cloud Run novo, não Postgres Python)
- Verifier: `c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest <path> -q --tb=short -x`
- Front types: `npx tsc --noEmit` em `frontend/`
- Commits **só se Marcelo pedir**
- Antes de agents/tools relatório: `.agent/rules/conferencia-fontes-pipeline.md` + `pipeline-fontes-deterministicas.md`
- Spec self-review: `.agent/rules/spec-self-review.md` (já ok nesta spec)

## File map

| File | Role |
|------|------|
| `scripts/batch/build_market_bundles.py` | Hard gate geocode em `_build_demografia` / `build_bundle` |
| `tools/test_build_market_bundle_geocode_gate.py` | TDD gate |
| `tools/maps_fallback.py` + `docs/GOOGLE_MAPS_SETUP.md` | Default documentado = código (`0`) |
| `pdf/html_builder.py` | Rótulos demografia honestos |
| `pdf/test_normalizacao_layout_coco.py` (ou novo) | Assert HTML sem “fonte real do bairro” |
| `frontend/.../ContextoMercadoCard.tsx` | Carimbo CNPJ por métrica |
| `frontend/.../DemografiaBairroCard.tsx` | Unidade distrito quando aplicável |
| `tools/cub_golden_validate.py` | Gate 27 UF + idade + ratio |
| `tools/test_cub_golden_validate.py` | TDD CUB |
| `docs/runbooks/CUB_PR_MENSAL.md` | Runbook PR |
| `backend/routers/internal_cron.py` | `/rfb-ingest` + `/mirror-health` |
| `tools/rfb_ingest_runner.py` | Orquestra loaders CNPJ+CNO |
| `tools/mirror_health.py` | Checks renda/PIB/censo |
| `db/migrations/20260806_monthly_rfb_cron.sql` | Target + schedule |
| `docs/runbooks/VPS_BR_RFB_INGEST.md` | Bring-up Hostinger/VPS BR |
| `.github/workflows/monthly-receita-batch.yml` | Docs: BQ histórico ≠ fresco |

---

# Wave 1 — Geocode hard gate + carimbos

### Task 1: Exceção + hard gate geocode no bundle builder

**Files:**
- Modify: `scripts/batch/build_market_bundles.py`
- Create: `tools/test_build_market_bundle_geocode_gate.py`

**Interfaces:**
- Produces: `class GeocodeBairroError(RuntimeError)` in `build_market_bundles.py` (or `tools/market_bundle_errors.py` if preferred single import)
- Consumes: `geocode_endereco` return dict with optional `lat`/`lng`

- [ ] **Step 1: Write failing test**

```python
# tools/test_build_market_bundle_geocode_gate.py
from unittest.mock import patch
import pytest

def test_build_demografia_raises_when_geocode_has_no_lat():
    from scripts.batch.build_market_bundles import GeocodeBairroError, _build_demografia

    with patch("tools.maps_tools.geocode_endereco", return_value={"erro": "REQUEST_DENIED"}):
        with patch("tools.ibge_tools.analise_demografica_completa", return_value={"codigo_ibge": "2304400"}):
            with patch("tools.bairro_renda_loader.enrich_demografia_bairro", side_effect=lambda b, *a, **k: b):
                with pytest.raises(GeocodeBairroError) as ei:
                    _build_demografia("Fortaleza", "Meireles", "CE")
    assert "geocode_bairro" in str(ei.value).lower() or "Meireles" in str(ei.value)
```

- [ ] **Step 2: Run test — expect FAIL (no GeocodeBairroError or still soft-fail)**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_build_market_bundle_geocode_gate.py -q --tb=short -x
```

Expected: FAIL (import/AttributeError or pass incorrectly if soft)

- [ ] **Step 3: Implement gate in `_build_demografia`**

Replace soft `censo = None if no lat` with raise when `(bairro or "").strip()` and `lat is None`:

```python
class GeocodeBairroError(RuntimeError):
    """Bundle must not publish without centroid for bairro demografia."""


# inside _build_demografia, after geo = geocode_endereco(...):
lat, lng = geo.get("lat"), geo.get("lng")
if lat is None or lng is None:
    err = geo.get("erro") or geo.get("status") or "sem lat/lng"
    raise GeocodeBairroError(
        f"geocode_bairro failed for {bairro!r}, {cidade}/{uf}: {err}"
    )
```

Keep try/except only around `demografia_setor_censo` (censo fail ≠ geocode fail). Do **not** catch `GeocodeBairroError` inside `_build_demografia`.

- [ ] **Step 4: `main()` — no write on gate fail**

```python
def main() -> int:
    ...
    try:
        bundle = build_bundle(...)
    except GeocodeBairroError as e:
        print(f"FATAL: {e}", file=sys.stderr)
        return 2
    path = save_market_bundle(...)
    ...
    return 0
```

- [ ] **Step 5: Re-run test — PASS**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_build_market_bundle_geocode_gate.py -q --tb=short -x
```

- [ ] **Step 6: Commit only if Marcelo asks**

```bash
git add scripts/batch/build_market_bundles.py tools/test_build_market_bundle_geocode_gate.py
git commit -m "fix(batch): hard-fail market bundle when bairro geocode misses"
```

---

### Task 2: Propagate geocode fail in weekly batch + stamp `missing_fields` when soft path unused

**Files:**
- Modify: `scripts/batch/run_weekly_market_batch.py` (or `tools/market_batch_runner.py` — follow call site of `build_bundle`)
- Modify: `scripts/batch/build_market_bundles.py` — if any path still soft-fails for empty bairro, document: empty bairro = skip censo (no raise)

**Interfaces:**
- Consumes: `GeocodeBairroError`
- Produces: batch exit ≠ 0 when any wave city raises

- [ ] **Step 1: Grep call sites**

```bash
rg -n "build_bundle|build_market_bundles" scripts/batch tools/market_batch_runner.py
```

- [ ] **Step 2: Ensure caller does not swallow GeocodeBairroError**

If loop `try/except Exception: continue`, change to re-raise `GeocodeBairroError` or count fatals and `return 2`.

- [ ] **Step 3: Smoke import**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -c "from scripts.batch.build_market_bundles import GeocodeBairroError; print(GeocodeBairroError)"
```

- [ ] **Step 4: Commit if asked**

---

### Task 3: Align MAPS_FALLBACK docs with code default `0`

**Files:**
- Modify: `docs/GOOGLE_MAPS_SETUP.md` (~L44 — remove “padrão =1”)
- Optionally one-line note in `scripts/batch/README.md`

- [ ] **Step 1: Fix doc**

State: default `MAPS_FALLBACK_ENABLED=0` (code in `tools/maps_fallback.py`); prod example may set `1` in `.env.production.example`.

- [ ] **Step 2: Commit if asked**

---

### Task 4: PDF demografia rótulos honestos

**Files:**
- Modify: `pdf/html_builder.py` (~L157–159 template)
- Modify: `pdf/html_builder.py` narrativa ~L1290 if still says “o bairro concentra” for raio pop
- Test: extend `pdf/test_normalizacao_layout_coco.py` or create `pdf/test_demografia_carimbo_html.py`

- [ ] **Step 1: Failing test on rendered HTML fragment**

```python
def test_pdf_demografia_header_not_fonte_real_do_bairro():
    from pdf.html_builder import _TEMPLATE
    assert "fonte real do bairro" not in _TEMPLATE
    assert "População (bairro)" not in _TEMPLATE
    assert "raio" in _TEMPLATE.lower() or "setores" in _TEMPLATE.lower()
```

- [ ] **Step 2: Run — expect FAIL**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest pdf/test_demografia_carimbo_html.py -q --tb=short -x
```

- [ ] **Step 3: Rewrite template headers**

```html
<th>Dimensão</th><th>Valor (base rotulada)</th>
...
<td>População (setores no raio do centróide)</td>
```

Ensure cell value still appends `· N setores (raio do centróide)` from `_contexto` (already ~L903).

- [ ] **Step 4: Soften narrativa** — “entorno do centróide / setores” not “o bairro concentra” when only raio pop exists.

- [ ] **Step 5: Tests PASS + commit if asked**

---

### Task 5: Front — carimbo CNPJ em `ContextoMercadoCard`

**Files:**
- Modify: `frontend/src/components/domain/ContextoMercadoCard.tsx`
- Types already on `mc` (`fonte_entrantes`, `cnpj_as_of`, `janela_q`, baixas fields)

**Interfaces:**
- Display helper (inline): `carimboCnpj(fonte, janela, asOf) -> string`

- [ ] **Step 1: Every CNPJ `IndicatorRow` shows fonte + janela/`as_of`**

Pattern for aberturas 90d / baixas 90d / Q metrics:

```tsx
<span className="text-[10px] text-muted-foreground font-mono font-normal">
  {[fonteEntrantes || 'RFB/Supabase', janelaLabel, cnpjAsOf ? `as_of ${cnpjAsOf}` : null]
    .filter(Boolean)
    .join(' · ')}
</span>
```

Where `janelaLabel` is `90d` or `janelaQLabel`. Do not leave bare numbers without stamp (except when `temDadosCnpj` false).

- [ ] **Step 2: Remove sole footer that only stamps entrantes if rows already stamped** — or keep footer as summary; avoid duplicate noise (prefer per-row mono line).

- [ ] **Step 3: Typecheck**

```bash
cd frontend && npx tsc --noEmit
```

Expected: exit 0

- [ ] **Step 4: Commit if asked**

---

### Task 6: Front — demografia unidade distrito

**Files:**
- Modify: `frontend/src/components/domain/DemografiaBairroCard.tsx`
- Check payload fields: `fonte` string containing `DISTRITO` / `unidade_tipo` if already on demografia block from adapters

- [ ] **Step 1: Read card props / `block.fonte`**

If `fonte` matches `/distrito/i` or `unidade_tipo === 'distrito'`, title/sub use **Distrito** not Bairro.

```tsx
const unidadeLabel =
  /distrito/i.test(String(block.fonte || '')) || block.unidade_tipo === 'distrito'
    ? 'Distrito'
    : 'Bairro'
```

- [ ] **Step 2: Keep existing setores · raio subline** (already good).

- [ ] **Step 3: `npx tsc --noEmit`**

- [ ] **Step 4: If PDF mercado table still says only “bairro” for renda distrito — optional one-line in `html_builder` using same fonte heuristic (same task if trivial).**

- [ ] **Step 5: Commit if asked**

---

# Wave 2 — CUB PR + gate

### Task 7: `validate_cub_golden` pure gate

**Files:**
- Create: `tools/cub_golden_validate.py`
- Create: `tools/test_cub_golden_validate.py`
- Reuse: `tools/cub_sinapi_compare.py` for ratio helpers optional
- Golden: `data/cub_pilot/cub_estadual_golden.json`
- SINAPI fixture: `tools/fixtures/cub_sinapi/sinapi_snapshot_golden.json`

**Interfaces:**
- Produces:
  - `UFS_BR: list[str]` — 27 siglas
  - `validate_cub_snapshot(cub: dict, *, sinapi: dict | None, hoje: date, max_idade_meses: int = 4) -> list[str]` — empty = ok; else error messages
  - Ratio band default: each UF with both CUB+SINAPI → ratio in `[1.04, 1.10]` (covers ~1.05–1.08 + slack); mean in `[1.05, 1.09]` when ≥20 UFs paired

- [ ] **Step 1: Failing tests**

```python
from datetime import date
from tools.cub_golden_validate import validate_cub_snapshot

def test_missing_uf_errors():
    bad = {"por_uf": {"CE": {"cub_m2": 1000, "periodo_ref": "junho 2026"}}, "data_coleta": "2026-07-13"}
    errs = validate_cub_snapshot(bad, sinapi=None, hoje=date(2026, 8, 6))
    assert any("27" in e or "UF" in e for e in errs)

def test_zero_cub_m2_errors():
    # build full 27 with one zero — assert error
    ...

def test_real_golden_passes_or_flags_stale_ms():
    import json
    from pathlib import Path
    cub = json.loads(Path("data/cub_pilot/cub_estadual_golden.json").read_text(encoding="utf-8"))
    errs = validate_cub_snapshot(cub, sinapi=None, hoje=date(2026, 8, 6), max_idade_meses=4)
    # MS maio 2025 may fail age — assert either ok or explicit MS/periodo message (document choice):
    # Spec: MS atrasado deve falhar OU exigir nota proxy — choose FAIL age unless fonte_uf contains "proxy" note on that UF
```

Decision locked in plan: **age fail** if parsed `periodo_ref` older than `max_idade_meses` **unless** `fonte_uf` contains `proxy` (case-insensitive). MS with old CUB and no proxy keyword → error (forces PR update or mark proxy).

- [ ] **Step 2: Run — FAIL**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_cub_golden_validate.py -q --tb=short -x
```

- [ ] **Step 3: Implement `tools/cub_golden_validate.py`**

Parse `periodo_ref` loosely (`junho 2026`, `maio 2025`) → first-of-month; idade vs `hoje`.

- [ ] **Step 4: CLI**

```python
# python -m tools.cub_golden_validate
# exit 0 if no errs else 1 print errs
```

- [ ] **Step 5: Tests PASS** — if current golden fails on MS, either update MS in a separate PR or add `proxy` to that UF’s `fonte_uf` **only after Marcelo ok**; do not silently weaken gate.

- [ ] **Step 6: Commit if asked**

---

### Task 8: Runbook CUB PR mensal + optional CI job

**Files:**
- Create: `docs/runbooks/CUB_PR_MENSAL.md`
- Optional: `.github/workflows/cub-golden-gate.yml` on PR paths `data/cub_pilot/**` + `tools/cub_golden_validate.py`

- [ ] **Step 1: Write runbook** (PT, produto+ops)

Steps: update `cub_estadual_golden.json` → run validate → open PR → merge → A4 reads golden via `load_cub_snapshot`.

- [ ] **Step 2: Optional GHA**

```yaml
# on pull_request paths: data/cub_pilot/**, tools/cub_golden_validate.py, tools/fixtures/cub_sinapi/**
# run: .venv or pip install + python -m tools.cub_golden_validate
```

- [ ] **Step 3: Commit if asked**

---

# Wave 3 — Ingest RFB/CNO + health (needs VPS BR)

> **Blocker:** Tasks 11–12 need reachable BR host URL. Tasks 9–10 + 13 can land in repo before VPS exists.

### Task 9: `rfb_ingest_runner` + cron endpoint

**Files:**
- Create: `tools/rfb_ingest_runner.py`
- Modify: `backend/routers/internal_cron.py`
- Create: `tests/test_internal_cron_rfb.py` (secret + dry stub)

**Interfaces:**
- Produces: `run_rfb_ingest(*, include_cnpj: bool = True, include_cno: bool = True, sync: bool = False) -> dict`
- HTTP: `POST /api/internal/cron/rfb-ingest` header `X-Cron-Secret`
- Body: `{ "include_cnpj": true, "include_cno": true, "sync": false }`
- Reuse `_check_cron_secret` / `MARKET_BATCH_CRON_SECRET`

- [ ] **Step 1: Failing test — 401 without secret**

Mirror pattern in `tests/test_internal_cron.py` for weekly endpoint.

- [ ] **Step 2: Implement runner** calling existing CLIs via subprocess or import:

```python
# Prefer import main functions if available; else subprocess:
# python -m tools.rfb_cnpj_fitness_loader --from-json $CNPJ_JSON_PATH --include-baixadas
# python -m tools.rfb_cno_loader ...
```

Env: `RFB_CNPJ_JSON_PATH`, `CNO_DATA_DIR` as already used by loaders.

- [ ] **Step 3: Async start like weekly batch** (`start_*_async`) to avoid pg_net 30s timeout — return `{status: started}` immediately.

- [ ] **Step 4: Tests PASS**

- [ ] **Step 5: Commit if asked**

---

### Task 10: Migration Supabase — `monthly_rfb_ingest` target + schedule

**Files:**
- Create: `db/migrations/20260806_monthly_rfb_cron.sql`

- [ ] **Step 1: SQL**

```sql
insert into gymsite.cron_http_targets (job_name, url, secret, enabled)
values (
  'monthly_rfb_ingest',
  'https://CONFIGURE_BR_HOST/api/internal/cron/rfb-ingest',
  'CONFIGURE_ME',
  false
)
on conflict (job_name) do nothing;

-- 1º domingo do mês 09:00 UTC — adjust if needed
select cron.schedule(
  'monthly_rfb_ingest_invoke',
  '0 9 * * 0',
  $$select gymsite.invoke_cron_http('monthly_rfb_ingest')$$
);
```

Note: “1º domingo” exact cron is hard in plain cron — document “todo domingo; loader no-ops if ref_month unchanged” **or** use `0 9 1-7 * 0` pattern. Prefer **document + weekly check with idempotent loader**.

- [ ] **Step 2: Apply via Supabase MCP/SQL only when Marcelo asks** (enabled=false until URL BR set).

- [ ] **Step 3: Commit migration file if asked**

---

### Task 11: Mirror health module + endpoint

**Files:**
- Create: `tools/mirror_health.py`
- Modify: `backend/routers/internal_cron.py` — `GET|POST /api/internal/cron/mirror-health`
- Create: `tools/test_mirror_health.py`

**Interfaces:**
- Produces: `check_mirrors(client) -> {ok: bool, checks: [{name, ok, detail}]}`
- Thresholds (v1 constants, tune later):

| Mirror | Min rows | Max age |
|--------|----------|---------|
| `renda_bairro` | 20000 | N/A (census static) or `updated_at` if column exists |
| `municipio_pib` | 5000 | 400 days if `ano`/`ref` present |
| `censo_setor` | 400000 | N/A static |
| `cnpj_fitness_estabelecimentos` | 30000 sit=02 optional | `ref_month` ≥ previous calendar month |

- [ ] **Step 1: Unit tests with fake client returning counts**

- [ ] **Step 2: Implement + wire HTTP (secret required)**

- [ ] **Step 3: Optional second cron target `mirror_health_daily`** — can be same migration or follow-up SQL.

- [ ] **Step 4: Commit if asked**

---

### Task 12: Runbook VPS BR bring-up

**Files:**
- Create: `docs/runbooks/VPS_BR_RFB_INGEST.md`

Content (produto+ops):
1. Provision Hostinger NVMe 4 (ingest-only) or 8 (API+ingest) — Ubuntu, **sem cPanel**
2. Docker or venv + same image/env as API (Supabase keys, paths JSON/CNO)
3. Expose only via Cloudflare Tunnel hostname → `.../api/internal/cron/rfb-ingest`
4. `UPDATE gymsite.cron_http_targets SET url=..., secret=..., enabled=true WHERE job_name='monthly_rfb_ingest'`
5. Smoke: `curl -H "X-Cron-Secret: ..." -d '{}' https://.../rfb-ingest`
6. Explicit: **no new gcloud**

- [ ] **Step 1: Write runbook**
- [ ] **Step 2: Link from `docs/PLAN_HETZNER_VPS_TUNNEL.md`** one line “RFB fresco = VPS BR, não Hetzner EU”
- [ ] **Step 3: Commit if asked**

---

### Task 13: Clarify GHA monthly-receita-batch = BQ historical only

**Files:**
- Modify: `.github/workflows/monthly-receita-batch.yml` comments/name in header
- Modify: `docs/arquitetura/COMPILADO_FONTES_DADOS.md` one row if still says “automatizada ❌” without pointing to W3

- [ ] **Step 1: Comment block** — “does NOT download RFB fresco; BR ingest = VPS + Supabase cron”
- [ ] **Step 2: Commit if asked**

---

## Plan self-review (vs spec)

| Spec requirement | Task |
|---|---|
| W1 hard gate geocode | T1–T2 |
| MAPS_FALLBACK doc vs code | T3 |
| PDF carimbos pop | T4 |
| Front ContextoMercadoCard CNPJ | T5 |
| Distrito label | T6 |
| CUB PR + validate 27/ratio/age | T7–T8 |
| No CUB scrape | Global + T8 |
| Supabase cron HTTP | T10 |
| VPS BR executor CNPJ+CNO | T9, T12 |
| Mirror health | T11 |
| No new gcloud | Global + T12–T13 |
| OSM out | Global / not tasked |
| Spec self-review rule | Already on spec |

**Gaps none.** Placeholder scan: none intentional; VPS URL = `CONFIGURE_BR_HOST` until ops fills.

---

## Execution handoff

Plan saved to `docs/superpowers/plans/2026-08-06-ops-p0-geocode-cub-carimbos.md`.

**Two execution options:**

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  

**2. Inline Execution** — this session, executing-plans with checkpoints  

**Which approach?** Start W1 (Tasks 1–6) even before VPS exists.
