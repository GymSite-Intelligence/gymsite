# Spec C — Polígono bairro IBGE (A2 + A3a) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify demografia (A2) and Maps competitors (A3a) on the same IBGE neighborhood polygon when available; fall back to current radii with honest stamps.

**Architecture:** Shared resolver (`tools/bairro_poligono.py`) returns a ring or `None`. Demografia aggregates census sectors whose centroids fall inside that ring (one `n_setores` for pop + age×sex). Competitor inclusion switches from R=1000 m to point-in-polygon when a ring exists. W1 is file-backed IBGE gpkg/GeoJSON (no FTP per report). W2 adds INDE/municipal adapters behind the same resolver.

**Tech Stack:** Python 3.11+, shapely/geopandas (já em `requirements.txt`), pytest, Jinja PDF, SearchAPI Maps via `competitor_tools`.

**Spec:** `docs/superpowers/specs/2026-08-06-spec-c-bairro-poligono-ibge-design.md`

## Global Constraints

- Consumidores W1: **A2 + A3a** (não A0)
- Gate Maps com polígono: **point-in-polygon** (não R=1000; não dual N)
- Sem polígono: pop `raio_m=1500`; Maps `RAIO_CONCORRENCIA_CANONICO_M=1000`
- Rótulo: “polígono IBGE do bairro (Censo 2022)” — nunca “limite oficial da prefeitura” só por IBGE
- Runtime **não** baixa FTP IBGE por relatório — só lê espelho local/`data/ibge_bairros/`
- Match: `tools.bairro_normalize.normalizar_bairro` (Coco ≡ Cocó)
- Zoneamento LUOS **fora** desta feature
- Verifier: `c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest <path> -q --tb=short -x`
- Commits **só se Marcelo pedir**
- Preview PDF/copy: `docs/superpowers/previews/` antes de ok humano (`.agent/rules/preview-aprovacao.md`)
- Antes de mexer A2/A3a/tools relatório: `.agent/rules/conferencia-fontes-pipeline.md` + `pipeline-fontes-deterministicas.md`

## File map

| File | Role |
|------|------|
| `tools/bairro_poligono.py` | Resolver + PIP + tipos `BairroPoligono` |
| `tools/test_bairro_poligono.py` | TDD resolver / PIP / match |
| `data/ibge_bairros/README.md` | Como baixar gpkg; o que é gitignored |
| `data/ibge_bairros/fixtures/coco_ce.geojson` | Polígono mínimo p/ testes (sem FTP) |
| `scripts/batch/ingest_ibge_bairros_uf.py` | Download gpkg UF → `data/ibge_bairros/{UF}.gpkg` |
| `tools/censo_setor_tools.py` | `demografia_setor_poligono(...)` |
| `tools/perfil_sexo_idade_tools.py` | `perfil_sexo_idade_poligono(...)` |
| `tools/demografia_bairro_tools.py` | Wire resolver → pop + pirâmide mesma lista |
| `tools/test_demografia_poligono.py` | n_setores pop == pirâmide |
| `tools/competitor_tools.py` | Gate PIP em `_places_para_concorrentes_bairro` (+ path SearchAPI equivalente) |
| `tools/test_competitor_poligono_gate.py` | Fora do polígono excluído mesmo &lt;1 km |
| `pdf/html_builder.py` | Carimbo polígono; nota 105≠183 só se bases diferem |
| `pdf/test_demografia_carimbo_html.py` (extend) | Assert copy polígono |
| `docs/superpowers/previews/2026-08-06-spec-c-w1-poligono.html` | Preview aprovação |
| `.agent/rules/conferencia-fontes-pipeline.md` | § demografia polígono + §9 Maps |
| `docs/arquitetura/PIPELINE_AGENTES.md` | A2/A3a fonte |
| `tools/bairro_poligono_adapters.py` (W2) | Adapters INDE/municipal |
| `tools/test_bairro_poligono_adapters.py` (W2) | Prioridade IBGE &gt; municipal |

---

# Wave 1 — IBGE file mirror + resolver + A2 + A3a + carimbos

### Task 1: PIP + tipo `BairroPoligono` + fixture Cocó

**Files:**
- Create: `tools/bairro_poligono.py`
- Create: `tools/test_bairro_poligono.py`
- Create: `data/ibge_bairros/fixtures/coco_ce.geojson`
- Create: `data/ibge_bairros/README.md`

**Interfaces:**
- Produces:
  - `BairroPoligono` TypedDict / dataclass: `cd_bairro: str | None`, `nm_bairro: str`, `id_municipio: str`, `ring: list[tuple[float, float]]` (lon, lat), `fonte: str`, `area_km2: float | None`
  - `point_in_ring(lon: float, lat: float, ring: list[tuple[float, float]]) -> bool`
  - `load_fixture_geojson(path: str | Path) -> list[BairroPoligono]`

- [ ] **Step 1: Write fixture GeoJSON**

Square around Cocó centroid (~-3.747, -38.482) large enough for tests (~2 km box). Properties: `CD_BAIRRO`, `NM_BAIRRO`=`Cocó`, `CD_MUN`=`2304400`.

```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "properties": {
      "CD_BAIRRO": "2304400015",
      "NM_BAIRRO": "Cocó",
      "CD_MUN": "2304400"
    },
    "geometry": {
      "type": "Polygon",
      "coordinates": [[
        [-38.500, -3.760], [-38.460, -3.760],
        [-38.460, -3.730], [-38.500, -3.730],
        [-38.500, -3.760]
      ]]
    }
  }]
}
```

- [ ] **Step 2: Write failing tests**

```python
# tools/test_bairro_poligono.py
from pathlib import Path
from tools.bairro_poligono import point_in_ring, load_fixture_geojson

FIX = Path("data/ibge_bairros/fixtures/coco_ce.geojson")

def test_point_inside_coco_fixture():
    polys = load_fixture_geojson(FIX)
    assert len(polys) == 1
    ring = polys[0]["ring"]
    assert point_in_ring(-38.482, -3.747, ring) is True

def test_point_outside_coco_fixture():
    ring = load_fixture_geojson(FIX)[0]["ring"]
    assert point_in_ring(-38.600, -3.900, ring) is False
```

- [ ] **Step 3: Run — expect FAIL (module missing)**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_bairro_poligono.py -q --tb=short -x
```

- [ ] **Step 4: Implement minimal `bairro_poligono.py`**

Use shapely `Point` + `Polygon.contains` (or ray casting). Prefer shapely — already in requirements. `ring` = exterior coords as `(lon, lat)`.

- [ ] **Step 5: Run — expect PASS**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_bairro_poligono.py -q --tb=short -x
```

- [ ] **Step 6: README** — FTP path IBGE `.../censo_2022/bairros/gpkg/UF/`, gitignore `*.gpkg`, fixture committed.

---

### Task 2: Resolver `resolver_bairro_poligono` (match nome + store injetável)

**Files:**
- Modify: `tools/bairro_poligono.py`
- Modify: `tools/test_bairro_poligono.py`

**Interfaces:**
- Consumes: `tools.bairro_normalize.normalizar_bairro`
- Produces:
  - `resolver_bairro_poligono(*, id_municipio: str | None, bairro: str, cidade: str | None = None, uf: str | None = None, _store: list[BairroPoligono] | None = None) -> BairroPoligono | None`
  - Match: same `id_municipio` (or CD_MUN) AND `normalizar_bairro(nm) == normalizar_bairro(bairro)`
  - Ambiguous multiple → first exact fold match; no invent

- [ ] **Step 1: Failing tests**

```python
def test_resolve_coco_sem_acento():
    from tools.bairro_poligono import resolver_bairro_poligono, load_fixture_geojson
    store = load_fixture_geojson(FIX)
    hit = resolver_bairro_poligono(id_municipio="2304400", bairro="Coco", _store=store)
    assert hit is not None
    assert hit["fonte"] == "ibge_bairro"
    assert hit["nm_bairro"] == "Cocó"

def test_resolve_miss_returns_none():
    store = load_fixture_geojson(FIX)
    assert resolver_bairro_poligono(id_municipio="2304400", bairro="Meireles", _store=store) is None
    assert resolver_bairro_poligono(id_municipio="9999999", bairro="Coco", _store=store) is None
```

- [ ] **Step 2: Run — FAIL**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_bairro_poligono.py::test_resolve_coco_sem_acento tools/test_bairro_poligono.py::test_resolve_miss_returns_none -q --tb=short -x
```

- [ ] **Step 3: Implement resolver** — if `_store` None, try load from `data/ibge_bairros/{UF}.gpkg` via geopandas when `uf` given; if file missing → `None` (no network).

- [ ] **Step 4: Run — PASS**

---

### Task 3: Demografia por polígono (pop + pirâmide mesma lista)

**Files:**
- Modify: `tools/censo_setor_tools.py`
- Modify: `tools/perfil_sexo_idade_tools.py`
- Modify: `tools/demografia_bairro_tools.py`
- Create: `tools/test_demografia_poligono.py`

**Interfaces:**
- Consumes: `resolver_bairro_poligono`, `point_in_ring`
- Produces:
  - `demografia_setor_poligono(id_municipio, ring, *, _rows: list[dict] | None = None) -> dict | None`  
    Keys: `populacao`, `domicilios`, `media_moradores`, `n_setores`, `raio_m=None`, `base="poligono_ibge_bairro"`, `fonte=...`
  - `perfil_sexo_idade_poligono(id_municipio, ring, *, _rows: list[dict] | None = None) -> dict | None`  
    Same segment schema as `perfil_sexo_idade_bairro`, but filter PIP (no `pop_alvo` fill)
  - `demografia_bairro`: if resolver hit → both from polígono; stamp `censo_base="poligono_ibge_bairro"`; else existing raio path + `censo_base="raio_fallback"`

- [ ] **Step 1: Failing test — same n_setores**

```python
# tools/test_demografia_poligono.py
from tools.bairro_poligono import load_fixture_geojson, resolver_bairro_poligono
from tools.censo_setor_tools import demografia_setor_poligono
from tools.perfil_sexo_idade_tools import perfil_sexo_idade_poligono

FIX_ROWS = [
    {"lat": -3.747, "lng": -38.482, "pessoas": 1000, "domicilios": 400,
     "h_total": 480, "m_total": 520, "h_15_24": 50, "m_15_24": 50,
     "h_25_39": 200, "m_25_39": 220, "h_40_59": 150, "m_40_59": 160,
     "h_60_mais": 80, "m_60_mais": 90},
    {"lat": -3.900, "lng": -38.600, "pessoas": 5000, "domicilios": 2000,  # fora
     "h_total": 2500, "m_total": 2500, "h_15_24": 100, "m_15_24": 100,
     "h_25_39": 1000, "m_25_39": 1000, "h_40_59": 800, "m_40_59": 800,
     "h_60_mais": 600, "m_60_mais": 600},
]

def test_pop_e_piramide_mesmo_n_setores():
    hit = resolver_bairro_poligono(id_municipio="2304400", bairro="Coco",
                                   _store=load_fixture_geojson("data/ibge_bairros/fixtures/coco_ce.geojson"))
    ring = hit["ring"]
    pop = demografia_setor_poligono("2304400", ring, _rows=FIX_ROWS)
    pir = perfil_sexo_idade_poligono("2304400", ring, _rows=FIX_ROWS)
    assert pop["n_setores"] == 1
    assert pir["n_setores"] == 1
    assert pop["populacao"] == 1000
```

- [ ] **Step 2: Run — FAIL**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_demografia_poligono.py -q --tb=short -x
```

- [ ] **Step 3: Implement** `demografia_setor_poligono` / `perfil_sexo_idade_poligono` (PIP on lat/lng; `_rows` bypasses Supabase).

- [ ] **Step 4: Wire `demografia_bairro`** after geocode + id_municipio:

```python
from tools.bairro_poligono import resolver_bairro_poligono
poly = resolver_bairro_poligono(id_municipio=id_municipio, bairro=bairro, cidade=cidade, uf=uf)
if poly and poly.get("ring"):
    censo = demografia_setor_poligono(id_municipio, poly["ring"])
    # ... fill out + censo_base
    perfil_bairro = perfil_sexo_idade_poligono(id_municipio, poly["ring"])
else:
    # existing demografia_setor_censo + perfil_sexo_idade_bairro
    out["censo_base"] = "raio_fallback"
```

Keep existing fields (`censo_n_setores`, `censo_raio_m` only on fallback).

- [ ] **Step 5: Run — PASS** (incl. existing `tools/test_censo_setor.py`, `tools/test_perfil_bairro_setor.py`)

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_demografia_poligono.py tools/test_censo_setor.py tools/test_perfil_bairro_setor.py -q --tb=short
```

---

### Task 4: Gate Maps point-in-polygon

**Files:**
- Modify: `tools/competitor_tools.py` (`_places_para_concorrentes_bairro` and SearchAPI-equivalent filter that applies `raio_metros`)
- Create: `tools/test_competitor_poligono_gate.py`

**Interfaces:**
- Consumes: `point_in_ring`, optional `ring` / `BairroPoligono` passed into discovery
- Produces: when `ring` provided, include place iff `point_in_ring(plng, plat, ring)`; ignore `raio_metros` for inclusion; set stamp field on each row or on envelope: `gate_espacial="poligono_ibge_bairro"` vs `"raio_1000m"`

Find all call sites that pass `raio_metros` into the filter (SearchAPI path + Places). Thread `ring: list[tuple[float,float]] | None = None` from macros that have `bairro`/`id_municipio` (resolve once per call).

- [ ] **Step 1: Failing test**

```python
# tools/test_competitor_poligono_gate.py
from tools.bairro_poligono import load_fixture_geojson, resolver_bairro_poligono
from tools.competitor_tools import _places_para_concorrentes_bairro

def test_place_dentro_1km_mas_fora_poligono_excluido():
    hit = resolver_bairro_poligono(id_municipio="2304400", bairro="Coco",
        _store=load_fixture_geojson("data/ibge_bairros/fixtures/coco_ce.geojson"))
    # ~800 m from centro but outside fixture box (tune coords vs fixture)
    places = [{
        "displayName": {"text": "Gym Fora"},
        "formattedAddress": "x",
        "location": {"latitude": -3.747, "longitude": -38.520},
        "types": ["gym"],
        "businessStatus": "OPERATIONAL",
        "id": "p1",
    }]
    out = _places_para_concorrentes_bairro(
        places, query="q", bairro="Coco",
        lat_centro=-3.747, lng_centro=-38.482,
        raio_metros=1000, ring=hit["ring"],
    )
    assert out == []

def test_place_longe_mas_dentro_poligono_incluido():
    hit = resolver_bairro_poligono(id_municipio="2304400", bairro="Coco",
        _store=load_fixture_geojson("data/ibge_bairros/fixtures/coco_ce.geojson"))
    places = [{
        "displayName": {"text": "Gym Dentro"},
        "formattedAddress": "x",
        "location": {"latitude": -3.745, "longitude": -38.490},
        "types": ["gym"],
        "businessStatus": "OPERATIONAL",
        "id": "p2",
    }]
    out = _places_para_concorrentes_bairro(
        places, query="q", bairro="Coco",
        lat_centro=-3.747, lng_centro=-38.482,
        raio_metros=100,  # would exclude by radius
        ring=hit["ring"],
    )
    assert len(out) == 1
    assert out[0]["gate_espacial"] == "poligono_ibge_bairro"
```

Adjust lat/lng in test to match fixture box after implementing.

- [ ] **Step 2: Run — FAIL**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_competitor_poligono_gate.py -q --tb=short -x
```

- [ ] **Step 3: Implement gate** in `_places_para_concorrentes_bairro`:

```python
def _places_para_concorrentes_bairro(..., ring=None):
    ...
    if ring:
        if not plat or not point_in_ring(plng, plat, ring):
            continue
        gate = "poligono_ibge_bairro"
    else:
        if plat and (dist_km * 1000.0) > raio_m:
            continue
        gate = "raio_1000m"
    out.append({..., "gate_espacial": gate})
```

Wire `ring` from `resolver_bairro_poligono` in `_descobrir_concorrentes_bairro` / SearchAPI discovery entrypoints (same pattern).

- [ ] **Step 4: Run — PASS** + smoke existing competitor tests that don't pass `ring`

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_competitor_poligono_gate.py tools/test_buscar_concorrentes_maps.py -q --tb=short
```

---

### Task 5: PDF / preview carimbos polígono

**Files:**
- Modify: `pdf/html_builder.py` (demografia table + pirâmide note)
- Modify: `pdf/test_demografia_carimbo_html.py` (or create if missing asserts)
- Create: `docs/superpowers/previews/2026-08-06-spec-c-w1-poligono.html`

**Interfaces:**
- Consumes: `demo_b.censo_base`, `censo_n_setores`, optional `cd_bairro`
- When `censo_base == "poligono_ibge_bairro"`: pop cell = `{N} hab · {n} setores · polígono IBGE bairro (Censo 2022)` — **no** “raio do centróide”
- Pirâmide note: if `n_setores_pop == n_setores_piramide`, short “mesma base polígono”; else keep dual-base warning (fallback only)

- [ ] **Step 1: Failing PDF test** — build HTML context with `censo_base=poligono_ibge_bairro`; assert “polígono IBGE” in HTML and “raio do centróide” **not** in pop line.

- [ ] **Step 2: Implement Jinja/context branches in `html_builder.py`**

- [ ] **Step 3: Write preview HTML** (mock Cocó: 1 n_setores, full age table, Maps stamp polígono)

- [ ] **Step 4: Open preview for Marcelo** — do not claim W1 done without OK

```bash
Start-Process "c:\Users\marce\gymsite\docs\superpowers\previews\2026-08-06-spec-c-w1-poligono.html"
```

---

### Task 6: Docs canônicos + ingest script UF

**Files:**
- Modify: `.agent/rules/conferencia-fontes-pipeline.md` (§ demografia + §9 Maps)
- Modify: `docs/arquitetura/PIPELINE_AGENTES.md` (A2/A3a bullets)
- Create: `scripts/batch/ingest_ibge_bairros_uf.py`
- Modify: `.gitignore` — `data/ibge_bairros/*.gpkg` (keep `fixtures/` and `README.md`)

**Interfaces:**
- Ingest CLI: `python scripts/batch/ingest_ibge_bairros_uf.py --uf CE` → writes `data/ibge_bairros/CE.gpkg` from IBGE geoftp (documented URL in README). Exit 0 on success; no silent empty file.

- [ ] **Step 1: Update conferencia** — demografia primária = polígono IBGE quando resolvido; Maps inclusão = PIP ou R=1000 fallback; carimbo obrigatório.

- [ ] **Step 2: Update PIPELINE_AGENTES** A2/A3a fonte lines.

- [ ] **Step 3: Ingest script** — httpx download UF gpkg; validate feature count &gt; 0; write path.

- [ ] **Step 4: Manual smoke (dev machine, not CI):** ingest CE; resolve Cocó against real gpkg; print `area_km2` + `cd_bairro`. Record one-liner in preview note if useful.

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe scripts/batch/ingest_ibge_bairros_uf.py --uf CE
```

---

# Wave 2 — Híbrido tapa-buraco (após W1 ok)

### Task 7: Adapter interface + prioridade IBGE &gt; municipal

**Files:**
- Create: `tools/bairro_poligono_adapters.py`
- Create: `tools/test_bairro_poligono_adapters.py`
- Modify: `tools/bairro_poligono.py` (`resolver_bairro_poligono` calls adapters only if IBGE miss)

**Interfaces:**
- `AdapterResult` same shape as `BairroPoligono` with `fonte` starting `inde_` or `prefeitura_`
- `list_adapters() -> list[Callable]`
- Priority: IBGE store first; then adapters in registration order
- W2 v1 ship: **one** real adapter OR one stub adapter behind flag `BAIRRO_POLIGONO_ADAPTERS=1` — choose DF **or** DataRio based on first paid gap; document choice in adapter module docstring

- [ ] **Step 1: Test priority** — IBGE hit wins even if adapter would return different ring.

- [ ] **Step 2: Test IBGE miss → adapter hit** with fake adapter.

- [ ] **Step 3: Implement** registration + wire.

- [ ] **Step 4: If real endpoint chosen** — fetch once, cache process-local, test match; else stub + skip network CI.

---

### Task 8: Preview W2 + docs gap list

**Files:**
- Create: `docs/superpowers/previews/2026-08-06-spec-c-w2-adapter.html`
- Modify: `data/ibge_bairros/README.md` — lista buracos conhecidos (TO, DF) + adapter status

- [ ] Preview before human OK
- [ ] Aceite Spec §5 W2 checklist

---

## Spec coverage (self-check)

| Spec requirement | Task |
|---|---|
| Resolver compartilhado | T1–T2 |
| A2 mesma lista setores | T3 |
| A3a PIP | T4 |
| Fallback raios + carimbo | T3–T5 |
| PDF/front rótulo IBGE | T5 |
| Docs PIPELINE + conferencia | T6 |
| Ingest sem FTP/runtime | T2 + T6 |
| W2 híbrido INDE/municipal | T7–T8 |
| Fora: Plano Diretor, CIB geom, A0, dual N | não no plano |

## Placeholder scan

Nenhum TBD. Storage W1 = arquivo `data/ibge_bairros/` (decisão travada). Adapter W2 concreto = primeira praça sem malha (escolha na T7 docstring, não bloqueia T1–T6).

---

## Execution

Plan saved to `docs/superpowers/plans/2026-08-06-spec-c-bairro-poligono-ibge.md`.

**Two options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline** — execute in this session with checkpoints  

Which?
