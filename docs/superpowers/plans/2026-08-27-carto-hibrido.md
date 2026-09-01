# CARTO híbrido A/B/C — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fase A deixa pontos→H3 numa tabela JSON (e um checklist para o Builder); Fase B expõe `GET /api/carto/hex-count` só com JWT; Fase C mostra o iframe do Builder no Explorar só logado.

**Architecture:** Warehouse CARTO produz hex (laboratório). GymSite **não** chama LDS. Backend lê um ficheiro JSON gerado pelo export (mesmo shape que o Workflow deve gravar); opcionalmente `CARTO_HEX_TABLE_PATH` aponta para uma cópia atualizada. Front de teste em `/carto-hex`. Explorar ganha modo Camadas CARTO se `VITE_CARTO_BUILDER_EMBED_URL` estiver definido.

**Tech Stack:** Python 3.11, `h3`, FastAPI, pytest, React 18, TanStack Router, JWT Supabase. CARTO Builder/Workflows = passos humanos no console (Task 1).

**Spec:** `docs/superpowers/specs/2026-08-27-carto-hibrido-design.md`

## Global Constraints

- Números: valor · base · fonte · janela. Sem tabela = 404 **sem** campo `n_academias`
- Sem PDF, A0–A9, MRLR, SearchAPI de aluguel, chat consultor
- Isoline produto = ORS. Sem `calculate_isolines` no site
- MapLibre permanece; iframe só `Boolean(user)` e URL de embed configurada
- Authz: qualquer user JWT válido (endpoint de teste, não IDOR de relatório). Sem JWT → 401
- Commits **only if Marcelo asks**
- Verifier BE: `c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest <path> -q --tb=short -x`
- Verifier FE: `npx tsc --noEmit` in `frontend/`
- H3 resolution **8** (`H3_RES = 8` in `tools/carto_hex.py`)
- Default table path: `data/carto/gym_hex_cidade.json` (repo). Override: env `CARTO_HEX_TABLE_PATH`

---

## File map

| File | Role |
|------|------|
| `data/carto/gym_hex_cidade.json` | Tabela estável (shape do Workflow) |
| `data/carto/WORKFLOW.md` | Como importar no `carto_dw` + SQL do fluxo |
| `scripts/batch/export_carto_gym_hex.py` | Pontos lat/lng → hex counts JSON |
| `tools/carto_hex.py` | Load table, lookup by lat/lng, stamp fields |
| `tools/test_carto_hex.py` | Unit tests (no network) |
| `backend/routers/carto.py` | `GET /api/carto/hex-count` |
| `tests/test_carto_hex_api.py` | 401 / 200 / 404 shape |
| `api.py` | `include_router` |
| `requirements.txt` | `h3` |
| `frontend/src/lib/cartoHex.ts` | fetch helper |
| `frontend/src/routes/CartoHexTestPage.tsx` | UI logada de teste |
| `frontend/src/router.tsx` | `/carto-hex` + `APP_PREFIXES` |
| `frontend/src/lib/nav-items.ts` | item sidebar |
| `frontend/src/components/layout/AuthenticatedSidebarLayout.tsx` | título |
| `frontend/src/routes/ExplorarPage.tsx` | modo iframe |
| `frontend/src/components/explorar/ExplorarControles.tsx` | botão Camadas CARTO |
| `frontend/.env.example` | `VITE_CARTO_BUILDER_EMBED_URL` |

---

### Task 1: Tabela JSON + export + checklist CARTO (Fase A)

**Files:**
- Create: `data/carto/gym_hex_cidade.json`
- Create: `data/carto/WORKFLOW.md`
- Create: `scripts/batch/export_carto_gym_hex.py`
- Modify: `requirements.txt` (add `h3>=4.1.0,<5`)

**Interfaces:**
- Consumes: list of `{name?, lat, lng, cidade}`
- Produces: JSON `{ "h3_res": 8, "fonte": "gym_hex_cidade", "gerado_em": ISO8601, "rows": [{ "hex": str, "n_academias": int, "cidade": str }] }`

- [ ] **Step 1: Add `h3` to requirements and install**

```text
h3>=4.1.0,<5
```

Run: `c:\Users\marce\gymsite\.venv\Scripts\pip.exe install "h3>=4.1.0,<5"`

Expected: package imports.

- [ ] **Step 2: Write `scripts/batch/export_carto_gym_hex.py`**

```python
#!/usr/bin/env python3
"""Aggregate gym points to H3 res=8 JSON for CARTO import / GymSite lookup."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

H3_RES = 8


def points_to_rows(points: list[dict], *, fonte: str) -> dict:
    import h3

    counts: Counter[tuple[str, str]] = Counter()
    for p in points:
        lat = float(p["lat"])
        lng = float(p["lng"])
        cidade = str(p.get("cidade") or "desconhecida").strip()
        cell = h3.latlng_to_cell(lat, lng, H3_RES)
        counts[(cell, cidade)] += 1
    gerado = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    rows = [
        {"hex": hx, "n_academias": n, "cidade": cidade}
        for (hx, cidade), n in sorted(counts.items())
    ]
    return {"h3_res": H3_RES, "fonte": fonte, "gerado_em": gerado, "rows": rows}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True, help="JSON array of points")
    p.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "carto" / "gym_hex_cidade.json",
    )
    p.add_argument("--fonte", default="gym_hex_cidade")
    args = p.parse_args()
    points = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(points, list):
        raise SystemExit("input must be a JSON array")
    payload = points_to_rows(points, fonte=args.fonte)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.output} rows={len(payload['rows'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Seed `data/carto/gym_hex_cidade.json` from three Fortaleza points (Cocó)**

Create `data/carto/_points_fortaleza_sample.json`:

```json
[
  {"name": "A", "lat": -3.7455, "lng": -38.4855, "cidade": "Fortaleza"},
  {"name": "B", "lat": -3.7460, "lng": -38.4860, "cidade": "Fortaleza"},
  {"name": "C", "lat": -3.8000, "lng": -38.5000, "cidade": "Fortaleza"}
]
```

Run:

```text
c:\Users\marce\gymsite\.venv\Scripts\python.exe scripts/batch/export_carto_gym_hex.py --input data/carto/_points_fortaleza_sample.json
```

Expected: `wrote ... rows=` 1 or 2 (A+B same hex likely; C may differ). File `gym_hex_cidade.json` has `h3_res`, `fonte`, `gerado_em`, `rows`.

- [ ] **Step 4: Write `data/carto/WORKFLOW.md`** (operator, no code deploy)

Content must include:

1. Import GeoJSON/CSV of the same points into CARTO DW dataset `shared` (connection `carto_dw`).
2. Workflow name `gym_hex_cidade`: H3 (res 8) → group by hex → count → **Save as table** (not only temp). Columns: `hex`, `n_academias`, `cidade`, plus CARTO `gerado_em` if the node allows.
3. Builder map: hex layer + points. **Not** the demo “Retail Store Performance”. Privacy private until Fase C.
4. After Workflow runs, export table or copy `n_academias` into `data/carto/gym_hex_cidade.json` (same schema) so the API stays in sync until BQ credentials exist.
5. Do not enable LDS isolines on this map for product clicks.
6. Aceite A: hex+pins visíveis; re-run workflow; MCP `explore_data` finds the table.

- [ ] **Step 5: Commit only if Marcelo asks**

```bash
git add requirements.txt data/carto scripts/batch/export_carto_gym_hex.py
git commit -m "feat(carto): H3 hex export seed for gym_hex_cidade"
```

---

### Task 2: `lookup_hex_count` (TDD)

**Files:**
- Create: `tools/carto_hex.py`
- Create: `tools/test_carto_hex.py`

**Interfaces:**
- Consumes: table dict from Task 1
- Produces:
  - `H3_RES = 8`
  - `load_hex_table(path: Path | None = None) -> dict`
  - `lookup_hex_count(lat: float, lng: float, table: dict) -> dict`  
    Success keys **only**: `n_academias` (int), `hex` (str), `cidade` (str), `fonte` (str), `gerado_em` (str), `base` (str)  
    `base` exact string: `"H3 res 8 da tabela gym_hex_cidade"`
  - Raises `HexCountNotFound` if no row for that cell

- [ ] **Step 1: Write failing tests** in `tools/test_carto_hex.py`

```python
from pathlib import Path

import pytest

from tools.carto_hex import HexCountNotFound, load_hex_table, lookup_hex_count

SAMPLE = Path("data/carto/gym_hex_cidade.json")


def test_lookup_coco_has_count():
    table = load_hex_table(SAMPLE)
    out = lookup_hex_count(-3.7455, -38.4855, table)
    assert out["n_academias"] >= 1
    assert out["cidade"] == "Fortaleza"
    assert "n_academias" in out
    assert out["base"] == "H3 res 8 da tabela gym_hex_cidade"
    assert out["fonte"]
    assert out["gerado_em"]
    assert out["hex"]


def test_lookup_ocean_raises_without_n():
    table = load_hex_table(SAMPLE)
    with pytest.raises(HexCountNotFound):
        lookup_hex_count(0.0, 0.0, table)
```

- [ ] **Step 2: Run tests — expect FAIL** (import error)

Run: `c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_carto_hex.py -q --tb=short`

Expected: FAIL (`ModuleNotFoundError` or import error)

- [ ] **Step 3: Implement `tools/carto_hex.py`**

```python
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import h3

H3_RES = 8
DEFAULT_TABLE = Path(__file__).resolve().parents[1] / "data" / "carto" / "gym_hex_cidade.json"
BASE_STAMP = "H3 res 8 da tabela gym_hex_cidade"


class HexCountNotFound(Exception):
    pass


def load_hex_table(path: Path | None = None) -> dict[str, Any]:
    raw = path or Path(os.getenv("CARTO_HEX_TABLE_PATH", str(DEFAULT_TABLE)))
    data = json.loads(raw.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("rows"), list):
        raise ValueError("hex table invalid")
    return data


def lookup_hex_count(lat: float, lng: float, table: dict[str, Any]) -> dict[str, Any]:
    cell = h3.latlng_to_cell(float(lat), float(lng), H3_RES)
    for row in table["rows"]:
        if str(row.get("hex")) == cell:
            n = int(row["n_academias"])
            return {
                "n_academias": n,
                "hex": cell,
                "cidade": str(row.get("cidade") or ""),
                "fonte": str(table.get("fonte") or "gym_hex_cidade"),
                "gerado_em": str(table.get("gerado_em") or ""),
                "base": BASE_STAMP,
            }
    raise HexCountNotFound(cell)
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_carto_hex.py -q --tb=short`

Expected: `2 passed`

- [ ] **Step 5: Commit only if Marcelo asks**

```bash
git add tools/carto_hex.py tools/test_carto_hex.py
git commit -m "feat(carto): lookup gym count by H3 cell"
```

---

### Task 3: `GET /api/carto/hex-count`

**Files:**
- Create: `backend/routers/carto.py`
- Create: `tests/test_carto_hex_api.py`
- Modify: `api.py` (after `explorar_router` include)

**Interfaces:**
- Consumes: `lookup_hex_count`, `load_hex_table`, `HexCountNotFound`; auth via `_user_id_from_request` copy from `backend/routers/explorar.py` (same `api._supabase_client` + Bearer)
- Produces: `GET /api/carto/hex-count?lat=&lng=`  
  - 401 `{"detail":"login necessario"}` if no user  
  - 200 body = exactly the lookup dict  
  - 404 `{"detail":"sem hex para este ponto"}` and `"n_academias" not in body`

- [ ] **Step 1: Write `tests/test_carto_hex_api.py`**

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        "backend.routers.carto._user_id_from_request",
        lambda request: "user-test",
    )
    from backend.routers.carto import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_hex_count_401_without_user(monkeypatch):
    monkeypatch.setattr(
        "backend.routers.carto._user_id_from_request",
        lambda request: None,
    )
    from backend.routers.carto import router

    app = FastAPI()
    app.include_router(router)
    r = TestClient(app).get("/api/carto/hex-count", params={"lat": -3.7455, "lng": -38.4855})
    assert r.status_code == 401
    assert "n_academias" not in r.json()


def test_hex_count_200(client):
    r = client.get("/api/carto/hex-count", params={"lat": -3.7455, "lng": -38.4855})
    assert r.status_code == 200
    body = r.json()
    assert body["n_academias"] >= 1
    assert body["base"] == "H3 res 8 da tabela gym_hex_cidade"


def test_hex_count_404_no_n_field(client):
    r = client.get("/api/carto/hex-count", params={"lat": 0, "lng": 0})
    assert r.status_code == 404
    assert "n_academias" not in r.json()
```

- [ ] **Step 2: Run — expect FAIL** (router missing)

Run: `c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tests/test_carto_hex_api.py -q --tb=short`

Expected: FAIL import

- [ ] **Step 3: Implement `backend/routers/carto.py`**

```python
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from tools.carto_hex import HexCountNotFound, load_hex_table, lookup_hex_count

router = APIRouter(prefix="/api/carto", tags=["carto"])


def _user_id_from_request(request: Request) -> str | None:
    auth = request.headers.get("authorization") or ""
    token = auth.removeprefix("Bearer ").strip()
    if not token:
        return None
    try:
        from api import _supabase_client

        sb = _supabase_client()
        user_resp = sb.auth.get_user(token)
        user = getattr(user_resp, "user", None)
        uid = getattr(user, "id", None) if user else None
        return str(uid) if uid else None
    except Exception:
        return None


@router.get("/hex-count")
def hex_count(
    request: Request,
    lat: float = Query(...),
    lng: float = Query(...),
):
    if not _user_id_from_request(request):
        raise HTTPException(status_code=401, detail="login necessario")
    try:
        table = load_hex_table()
        return lookup_hex_count(lat, lng, table)
    except HexCountNotFound:
        raise HTTPException(status_code=404, detail="sem hex para este ponto") from None
```

- [ ] **Step 4: Mount in `api.py`**

```python
from backend.routers.carto import router as carto_router
app.include_router(carto_router)
```

Place next to `app.include_router(explorar_router)`.

- [ ] **Step 5: Run tests — expect PASS**

Run: `c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tests/test_carto_hex_api.py tools/test_carto_hex.py -q --tb=short`

Expected: all passed

- [ ] **Step 6: Commit only if Marcelo asks**

```bash
git add backend/routers/carto.py tests/test_carto_hex_api.py api.py
git commit -m "feat(api): GET /api/carto/hex-count for logged-in tests"
```

---

### Task 4: Página `/carto-hex` (UI teste logada)

**Files:**
- Create: `frontend/src/lib/cartoHex.ts`
- Create: `frontend/src/routes/CartoHexTestPage.tsx`
- Modify: `frontend/src/router.tsx` (`APP_PREFIXES` include `'/carto-hex'`, route, `routeTree`)
- Modify: `frontend/src/lib/nav-items.ts`
- Modify: `frontend/src/components/layout/AuthenticatedSidebarLayout.tsx` (`PAGE_TITLES['/carto-hex'] = 'Hex CARTO'`)

**Interfaces:**
- Consumes: `API_BASE`, `supabase.auth.getSession` Bearer (same as `useLlmConfig`)
- Produces: `fetchHexCount(lat: number, lng: number): Promise<HexCountOk>`  
  Type `HexCountOk = { n_academias: number; hex: string; cidade: string; fonte: string; gerado_em: string; base: string }`  
  On 401/404 throw `Error` with message; never invent `n_academias`

- [ ] **Step 1: `frontend/src/lib/cartoHex.ts`**

```ts
import { API_BASE, supabase } from '@/lib/supabase'

export type HexCountOk = {
  n_academias: number
  hex: string
  cidade: string
  fonte: string
  gerado_em: string
  base: string
}

export async function fetchHexCount(lat: number, lng: number): Promise<HexCountOk> {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  const headers: HeadersInit = {}
  if (token) headers.Authorization = `Bearer ${token}`
  const q = new URLSearchParams({ lat: String(lat), lng: String(lng) })
  const res = await fetch(`${API_BASE}/api/carto/hex-count?${q}`, { headers })
  const body = (await res.json()) as Record<string, unknown>
  if (!res.ok) {
    throw new Error(String(body.detail ?? `erro ${res.status}`))
  }
  if (typeof body.n_academias !== 'number') {
    throw new Error('resposta sem contagem')
  }
  return body as HexCountOk
}
```

- [ ] **Step 2: `CartoHexTestPage.tsx`**

Page: two number inputs default `-3.7455` / `-38.4855`, button “Buscar hex”, show `n_academias` **and** the stamp line `{n_academias} academias · {base} · {fonte} · {gerado_em}`. On error, show the message only (no fake number). Use existing tokens (`text-foreground`, `bg-card`, `border-border`, `bg-primary`). Keep file under 200 lines.

- [ ] **Step 3: Wire router**

Copy the pattern of `cnoObrasRoute`: `createRoute({ getParentRoute: () => rootRoute, path: '/carto-hex', component: CartoHexTestPage })`. Add `'/carto-hex'` to `APP_PREFIXES`. Add the route to the `routeTree` array next to other app routes.

`nav-items.ts`: append `{ title: 'Hex CARTO', to: '/carto-hex', icon: HexagonIcon }` — import `HexagonIcon` from `lucide-react`.

- [ ] **Step 4: `npx tsc --noEmit` in `frontend/`**

Expected: exit 0

- [ ] **Step 5: Manual** — login, open `/carto-hex`, buscar Cocó → vê número + carimbo; ponto `0,0` → mensagem de erro sem número.

- [ ] **Step 6: Commit only if Marcelo asks**

```bash
git add frontend/src/lib/cartoHex.ts frontend/src/routes/CartoHexTestPage.tsx frontend/src/router.tsx frontend/src/lib/nav-items.ts frontend/src/components/layout/AuthenticatedSidebarLayout.tsx
git commit -m "feat(ui): logged-in CARTO hex count test page"
```

---

### Task 5: Explorar — Camadas CARTO (iframe logado)

**Files:**
- Modify: `frontend/src/components/explorar/ExplorarControles.tsx`
- Modify: `frontend/src/routes/ExplorarPage.tsx`
- Create or modify: `frontend/.env.example` with `VITE_CARTO_BUILDER_EMBED_URL=`

**Interfaces:**
- Consumes: `useAuth().user`, `import.meta.env.VITE_CARTO_BUILDER_EMBED_URL as string | undefined`
- Produces: `cartoCamadasOn: boolean` — true only if `loggedIn && Boolean(embedUrl) && toggle`. When true, render `<iframe title="Camadas CARTO" src={embedUrl} className="h-full w-full border-0" />` instead of `ExplorarMap`. Do **not** call `useExplorarIsocronas` fetch while `cartoCamadasOn` (pass `enabled: !cartoCamadasOn` or skip effect). Anonymous: no button, no iframe.

- [ ] **Step 1: Add optional props to `ExplorarControles`**

```ts
cartoEmbedAvailable?: boolean
cartoCamadasOn?: boolean
onCartoCamadas?: (on: boolean) => void
```

If `cartoEmbedAvailable`, render a button labeled `Camadas CARTO` (same chrome classes as existing toggles). `aria-pressed={cartoCamadasOn}`. Clicking calls `onCartoCamadas!(!cartoCamadasOn)`.

- [ ] **Step 2: `ExplorarPage`**

```ts
const cartoEmbed = String(import.meta.env.VITE_CARTO_BUILDER_EMBED_URL || '').trim()
const cartoEmbedAvailable = loggedIn && cartoEmbed.length > 0
const [cartoCamadasOn, setCartoCamadasOn] = useState(false)
```

When `!cartoEmbedAvailable && cartoCamadasOn`, force `setCartoCamadasOn(false)` in an effect.

Where `ExplorarMap` is rendered: if `cartoCamadasOn && cartoEmbedAvailable`, iframe; else existing map.

Do not start ORS when `cartoCamadasOn` (gate the isocronas hook/query).

- [ ] **Step 3: `npx tsc --noEmit`**

Expected: exit 0

- [ ] **Step 4: Manual** — logged out `/explorar`: no Camadas CARTO. Logged in without env: no button. Logged in with embed URL of the **product** map (not US retail demo): iframe. Toggle off: MapLibre + ORS back.

- [ ] **Step 5: Commit only if Marcelo asks**

```bash
git add frontend/src/components/explorar/ExplorarControles.tsx frontend/src/routes/ExplorarPage.tsx frontend/.env.example
git commit -m "feat(explorar): logged-in CARTO Builder iframe mode"
```

---

## Self-review

| Spec § | Task |
|--------|------|
| Fase A import + workflow + Builder | Task 1 `WORKFLOW.md` + JSON seed |
| Tabela `hex`, `n_academias`, `cidade`, fonte, gerado_em | Task 1–2 |
| GET autenticado + 401/404 sem número | Task 3 |
| UI teste logada | Task 4 |
| Iframe Explorar só logado; MapLibre fica; ORS não no mesmo modo | Task 5 |
| Fora: PDF, anônimo, MRLR, Receita | not in tasks |
| Named sources | omitted (YAGNI; B is file/JSON) |

**Placeholder scan:** HTTP path locked `GET /api/carto/hex-count`. Embed URL is env, not TBD in code. BQ live read omitted until credentials — JSON file is the contract.

**Types:** `HexCountOk` / lookup dict keys match across Tasks 2–4.
