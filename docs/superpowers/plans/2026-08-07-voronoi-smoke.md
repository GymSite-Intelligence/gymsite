# Voronoi Smoke — Implementation Plan (W2.1a + W2.1b)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compute classic + weighted Voronoi pool smoke next to Absorção; show a short experimental note in PDF/app; **do not** change fresco/roubo label or Oceano verdict.

**Architecture:** Pure geo compute in `tools/voronoi_atratividade.py` (scipy Voronoi + shapely clip). `attach_absorcao_margem_fresca` appends `voronoi_smoke` after the existing payload. PDF/React read classic numbers only for the note. Weighted stays JSON-only.

**Tech Stack:** Python 3.11+, scipy, shapely, pytest, existing Absorção attach, Jinja PDF, React card.

**Spec:** `docs/superpowers/specs/2026-08-07-voronoi-smoke-design.md`

## Global Constraints

- Smoke **parallel** — never overwrite `pool_primario`, `margem_fresca`, `rotulo`, `base_espacial`
- `base_espacial` stays `poligono_ibge` | `raio_fallback` only in this plan
- Pool smoke preferencial: pirâmide na célula (`estoque_form × interesse × pen`); fallback escala `round(pool_ref * pop_celula / pop_bairro)`
- Classic Voronoi for PDF/app note; weighted (`area_proxy_*` weight) JSON only
- Fail soft: any Voronoi error → `status=indisponivel`; Absorção attach still returns OK
- Vernáculo na nota: no `pool`, `pen.`, `scipy`, param IDs (`.agent/rules/leitura-executiva-pdf.md`)
- Preview PDF = `gerar_html` + open browser (`.agent/rules/preview-aprovacao.md`)
- Verifier: `c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest <path> -q --tb=short -x`
- Frontend check: `npx tsc --noEmit` in `frontend/`
- Commits **só se Marcelo pedir**
- Before pipeline touch: `.agent/rules/conferencia-fontes-pipeline.md`

---

## File map

| File | Role |
|------|------|
| `tools/voronoi_atratividade.py` | Sites → cells → pop/pirâmide → smoke dict |
| `tools/test_voronoi_atratividade.py` | TDD classic / weighted / pirâmide / indisponivel |
| `tools/censo_setor_tools.py` | `carregar_setores_idade_sexo` bbox+páginas |
| `tools/absorcao_margem_fresca.py` | Call smoke after result; nest under `voronoi_smoke` |
| `tools/test_absorcao_margem_fresca.py` | Assert smoke nested; rotulo unchanged |
| `pdf/html_builder.py` | Nota experimental if `status=ok` |
| `pdf/test_absorcao_html.py` | Assert note + no rotulo flip |
| `frontend/.../AbsorcaoMargemFrescaCard.tsx` | Same note |
| `frontend/.../useRelatorioDetail.ts` | Type `voronoi_smoke` |
| `docs/arquitetura/PIPELINE_AGENTES.md` | One bullet |
| `.agent/rules/conferencia-fontes-pipeline.md` | § smoke |
| `docs/superpowers/previews/2026-08-07-voronoi-smoke.html` | `gerar_html` dump |

**Out of this plan:** auto “melhor score fica”; `base_espacial=voronoi`; map drawing; pyramid-in-cell; park mix-by-cell.

---

# Wave W2.1a — Core + attach

### Task 1: `voronoi_atratividade` — classic cell + scale

**Files:**
- Create: `tools/voronoi_atratividade.py`
- Create: `tools/test_voronoi_atratividade.py`

**Interfaces:**
- Produces:
  - `Site = TypedDict` with `lat`, `lng`, `peso` (float), `is_candidato` (bool)
  - `compute_voronoi_smoke(*, sites, ring, setores, pool_ref, pop_bairro) -> dict`
  - Return keys per spec §5 (`status`, `pool_voronoi`, `delta_pct`, …)

- [ ] **Step 1: Failing tests**

```python
# tools/test_voronoi_atratividade.py
def test_smoke_classic_scales_pool():
    from tools.voronoi_atratividade import compute_voronoi_smoke

    # Square ring; candidato west, rival east; setores with pop on both sides
    ring = [(-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1)]  # lon, lat
    sites = [
        {"lat": 0.0, "lng": -0.5, "peso": 1500.0, "is_candidato": True},
        {"lat": 0.0, "lng": 0.5, "peso": 1500.0, "is_candidato": False},
    ]
    setores = [
        {"lat": 0.0, "lng": -0.4, "pessoas": 800},
        {"lat": 0.0, "lng": 0.4, "pessoas": 200},
    ]
    out = compute_voronoi_smoke(
        sites=sites, ring=ring, setores=setores, pool_ref=1000, pop_bairro=1000
    )
    assert out["status"] == "ok"
    assert out["pop_celula"] == 800
    assert out["pool_ref"] == 1000
    assert out["pool_voronoi"] == 800  # 1000 * 800/1000
    assert out["delta_pct"] == -0.2
    assert out["pool_voronoi_ponderado"] is not None


def test_smoke_indisponivel_sem_candidato_coords():
    from tools.voronoi_atratividade import compute_voronoi_smoke

    out = compute_voronoi_smoke(
        sites=[{"lat": None, "lng": None, "peso": 1500, "is_candidato": True}],
        ring=[(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)],
        setores=[],
        pool_ref=100,
        pop_bairro=100,
    )
    assert out["status"] == "indisponivel"
    assert out["motivo"] in ("sem_coords", "poucos_pontos")
```

- [ ] **Step 2: Run — FAIL**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_voronoi_atratividade.py -q --tb=short -x
```

Expected: FAIL ImportError / missing module

- [ ] **Step 3: Implement minimal**

```python
# tools/voronoi_atratividade.py — sketch
"""Voronoi smoke: classic + weighted cells × censo_setor centroids; scale pool_ref."""
from __future__ import annotations
from typing import Any

def _indisponivel(motivo: str, **extra: Any) -> dict[str, Any]:
    return {
        "status": "indisponivel",
        "motivo": motivo,
        "pop_bairro": extra.get("pop_bairro"),
        "pop_celula": None,
        "pop_celula_ponderada": None,
        "pool_ref": extra.get("pool_ref"),
        "pool_voronoi": None,
        "pool_voronoi_ponderado": None,
        "delta_pct": None,
        "n_sites": extra.get("n_sites", 0),
        "n_setores_celula": None,
        "peso_candidato": None,
        "carimbo": f"indisponivel · {motivo} · voronoi_smoke · n/a",
    }

def compute_voronoi_smoke(
    *,
    sites: list[dict[str, Any]],
    ring: list[tuple[float, float]] | None,
    setores: list[dict[str, Any]],
    pool_ref: int,
    pop_bairro: int,
) -> dict[str, Any]:
    # 1) validate ring, ≥2 sites with finite lat/lng, exactly one is_candidato
    # 2) classic: scipy.spatial.Voronoi on (lng, lat); build cell polygon for candidato
    #    (use shapely; infinite ridges → clip with large bbox then ∩ Polygon(ring))
    # 3) weighted: approximate MW-Voronoi by nearest site in metric
    #    dist / sqrt(peso)  (peso = area_proxy m²); same clip
    # 4) pop_celula = sum pessoas for setor centroids in classic cell
    # 5) pop_celula_ponderada = same for weighted cell
    # 6) scale pools; delta_pct = (pool_voronoi - pool_ref) / pool_ref if pool_ref else None
    ...
```

**Weighted note:** full power diagram optional later; W2.1a uses **multiplicatively weighted nearest** `d/sqrt(w)` — document in module docstring as proxy for `voronoi_ponderado`.

**Classic cell from scipy:** prefer known pattern — Voronoi ridge → shapely polygon per point, or use `geopandas`/manual. If only 2 sites, perpendicular bisector split of ring is enough and more stable — implement `_cell_classic_two_or_more` with scipy for N≥3 and bisector for N=2.

- [ ] **Step 4: Run — PASS**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_voronoi_atratividade.py -q --tb=short -x
```

- [ ] **Step 5: Commit only if Marcelo asks**

---

### Task 2: Attach hook — nest `voronoi_smoke`

**Files:**
- Modify: `tools/absorcao_margem_fresca.py` (`attach_absorcao_margem_fresca`)
- Modify: `tools/test_absorcao_margem_fresca.py`

**Interfaces:**
- Consumes: `compute_voronoi_smoke`
- Produces: `parsed["absorcao_margem_fresca"]["voronoi_smoke"]`
- Reads from state (best-effort):
  - candidato lat/lng: `state` top1 / `area` candidato / `input_params`
  - concorrentes: lista espacial Matriz (`concorrentes_espaciais_from_state`) + lat/lng
  - ring: `state["bairro_poligono"]["ring"]` or equivalent Spec C key (inspect `tools/bairro_poligono.py` / demografia state — if missing → indisponivel `sem_poligono`)
  - setores: optional inject `_setores` for tests; prod may skip live SB in unit tests
  - `pop_bairro` / `pool_ref` from absorção result + demografia

- [ ] **Step 1: Failing test — smoke nested, rotulo intact**

```python
def test_attach_adds_voronoi_smoke_without_changing_rotulo(monkeypatch):
    from tools import absorcao_margem_fresca as m

    def fake_smoke(**kwargs):
        return {
            "status": "ok",
            "motivo": None,
            "pop_bairro": 1000,
            "pop_celula": 400,
            "pop_celula_ponderada": 350,
            "pool_ref": kwargs["pool_ref"],
            "pool_voronoi": int(round(kwargs["pool_ref"] * 0.4)),
            "pool_voronoi_ponderado": int(round(kwargs["pool_ref"] * 0.35)),
            "delta_pct": -0.6,
            "n_sites": 2,
            "n_setores_celula": 1,
            "peso_candidato": 1500.0,
            "carimbo": "ok · smoke · IBGE · n/a",
        }

    monkeypatch.setattr(
        "tools.voronoi_atratividade.compute_voronoi_smoke", fake_smoke, raising=False
    )
    # also patch import path used inside attach if absolute
    monkeypatch.setattr(m, "compute_voronoi_smoke", fake_smoke, raising=False)

    state = {
        "demografia_bairro": {"populacao": 60165, "renda_media_per_capita": 4812},
        "concorrentes_brutos": [
            {"nome": "A", "lat": -3.75, "lng": -38.48, "gate_espacial": "poligono_ibge_bairro"},
            {"nome": "B", "lat": -3.76, "lng": -38.47, "gate_espacial": "poligono_ibge_bairro"},
        ],
        "area_m2": 1500,
        "candidato_lat": -3.755,
        "candidato_lng": -38.475,
        "bairro_poligono": {
            "ring": [(-38.50, -3.78), (-38.45, -3.78), (-38.45, -3.73), (-38.50, -3.73), (-38.50, -3.78)]
        },
    }
    parsed: dict = {"veredito_posicionamento": "OCEANO_AZUL"}
    # If attach needs setores for real path, monkeypatch loader to []
    out = m.attach_absorcao_margem_fresca(state, parsed)
    assert out is not None
    abs_ = parsed["absorcao_margem_fresca"]
    rotulo_before_shape = abs_["rotulo"]
    assert "voronoi_smoke" in abs_
    assert abs_["voronoi_smoke"]["status"] == "ok"
    assert abs_["rotulo"] == rotulo_before_shape
    assert abs_["base_espacial"] in ("poligono_ibge", "raio_fallback")
```

Wire attach so it **imports** `compute_voronoi_smoke` inside try/except; on failure set indisponivel without raising.

Resolve coords helper:

```python
def _candidato_xy(state: dict) -> tuple[float | None, float | None]:
    for a, b in (("candidato_lat", "candidato_lng"), ("lat", "lng")):
        if state.get(a) is not None and state.get(b) is not None:
            return float(state[a]), float(state[b])
    # top1 candidato in state["candidatos_geoscout"] / listing — inspect existing keys
    ...
```

- [ ] **Step 2: Run — FAIL** (no voronoi_smoke key)

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_absorcao_margem_fresca.py::test_attach_adds_voronoi_smoke_without_changing_rotulo -q --tb=short -x
```

- [ ] **Step 3: Implement attach nest** after `parsed["absorcao_margem_fresca"] = result` and **before** `aplicar_veto_oceano_por_roubo` (order: smoke must not affect veto inputs). Prefer: after veto still OK — smoke does not read veredito. Spec: after result built.

```python
    parsed["absorcao_margem_fresca"] = result
    try:
        from tools.voronoi_atratividade import compute_voronoi_smoke, sites_from_state
        smoke = compute_voronoi_smoke(**sites_from_state(state, result))
        result["voronoi_smoke"] = smoke
        parsed["absorcao_margem_fresca"] = result
    except Exception:
        result["voronoi_smoke"] = {
            "status": "indisponivel",
            "motivo": "erro_interno",
            ...
        }
    aplicar_veto_oceano_por_roubo(parsed)
```

- [ ] **Step 4: Run full absorção + voronoi suites — PASS**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_voronoi_atratividade.py tools/test_absorcao_margem_fresca.py -q --tb=short
```

- [ ] **Step 5: Docs one-liners**

- `docs/arquitetura/PIPELINE_AGENTES.md` — Absorção bullet: `voronoi_smoke` experimental, não muda rótulo.
- `.agent/rules/conferencia-fontes-pipeline.md` — §9.x smoke Voronoi.

- [ ] **Step 6: Commit only if Marcelo asks**

---

# Wave W2.1b — PDF + React note

### Task 3: PDF nota

**Files:**
- Modify: `pdf/html_builder.py` (absorção section + `_contexto`)
- Modify: `pdf/test_absorcao_html.py`

**Interfaces:**
- Consumes: `absorcao_margem_fresca.voronoi_smoke`
- Produces: `absorcao.nota_voronoi` string | None

- [ ] **Step 1: Failing test**

```python
def test_html_voronoi_note_classic_only():
    # model with rotulo roubo + voronoi_smoke ok pool_voronoi=500 delta=-0.5
    html = gerar_html(model)
    assert "Leitura espacial (experimental)" in html
    assert "500" in html or "500 alunos" in html
    assert "ainda" in html.lower()  # ainda usa o bairro
    # weighted number must NOT appear as the headline figure if different
    assert "scipy" not in html.lower()
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Helper + template**

```python
def _nota_voronoi_smoke(smoke: dict | None) -> str | None:
    if not isinstance(smoke, dict) or smoke.get("status") != "ok":
        return None
    pv = smoke.get("pool_voronoi")
    d = smoke.get("delta_pct")
    if pv is None or d is None:
        return None
    pct = f"{abs(d)*100:.0f}%"
    sentido = "menor" if d < 0 else "maior"
    return (
        f"Leitura espacial (experimental): se usássemos a área de influência entre academias "
        f"(Voronoi clássico), o potencial no público do formulário seria cerca de "
        f"{_int(pv)} alunos ({pct} {sentido} que o bairro inteiro). "
        f"O veredito fresco/roubo ainda usa o bairro. Medição interna — não muda a decisão nesta versão."
    )
```

In template after conclusão card:

```jinja
{% if absorcao.nota_voronoi %}
<div class="note" style="margin-top:8px; border-left:3px solid #94A3B8; padding-left:8px;">{{ absorcao.nota_voronoi }}</div>
{% endif %}
```

- [ ] **Step 4: PASS + preview**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest pdf/test_absorcao_html.py -q --tb=short
```

Dump `gerar_html` → `docs/superpowers/previews/2026-08-07-voronoi-smoke.html` → `Start-Process` that file.

- [ ] **Step 5: Commit only if Marcelo asks**

---

### Task 4: React card note

**Files:**
- Modify: `frontend/src/hooks/useRelatorioDetail.ts` (`AbsorcaoMargemFrescaJSON.voronoi_smoke`)
- Modify: `frontend/src/components/domain/AbsorcaoMargemFrescaCard.tsx`
- Optional: update `docs/superpowers/previews/2026-08-07-absorcao-react-card.html`

**Interfaces:**
- Same copy as PDF helper (duplicate short PT string in TS — OK for W2.1b; do not share Python)

- [ ] **Step 1: Extend type**

```typescript
voronoi_smoke?: {
  status?: 'ok' | 'indisponivel' | string
  pool_voronoi?: number | null
  delta_pct?: number | null
  motivo?: string | null
} | null
```

- [ ] **Step 2: Render note under conclusão** when `status === 'ok'`

- [ ] **Step 3: `npx tsc --noEmit` in `frontend/` — PASS**

- [ ] **Step 4: Commit only if Marcelo asks**

---

## Spec coverage

| Spec item | Task |
|-----------|------|
| `voronoi_atratividade.py` classic+weighted | T1 |
| Soft fail / indisponivel | T1–T2 |
| Nest under absorção; no rotulo change | T2 |
| PDF note classic only | T3 |
| React note | T4 |
| Docs PIPELINE + conferência | T2 |
| Preview `gerar_html` | T3 |
| Ligar / melhor score / map | Out |

---

## Self-review (plan)

- [x] Header + global constraints present
- [x] TDD steps with exact pytest commands
- [x] File map complete
- [x] Out of plan explicit
- [x] Commits gated on Marcelo
