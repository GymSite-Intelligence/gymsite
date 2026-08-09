# Explorar no mapa W1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `/explorar` mapa-first (OSM claro+escuro, pin, lente 500m/1km/bairro) that runs a **light** Absorção+Maps analyze — logged-in and degustação — **without** OndeAbrir-style 0–10 score.

**Architecture:** New sync-ish API `POST /api/explorar/analisar` builds a minimal state (geocode → ring/raio → SearchAPI academias → setores idade → `absorcao_margem_fresca` + optional `voronoi_smoke`) and returns JSON for the panel. Frontend: full-bleed `pigeon-maps` (reuse `/mapa` OSM pattern) + bottom bar + side panel reusing `AbsorcaoMargemFrescaCard`. Degustação reuses Turnstile + email entitlement of `/api/site-agent/analise` (no parallel funil).

**Tech Stack:** FastAPI, `tools/maps_tools.geocode_endereco`, SearchAPI Maps, `tools/absorcao_margem_fresca`, React + TanStack Router, `pigeon-maps`, pytest, `npx tsc --noEmit`.

**Spec:** `docs/superpowers/specs/2026-08-07-explorar-mapa-design.md` (W1 only)

## Global Constraints

- No score 0–10 · no “oportunidade clara” genérico · no aluguel R$ 35–65 heurístico
- One spatial base per response: lente escolhida = mesma base em Absorção + lista + pins
- Numbers carry carimbo (valor · base · fonte · janela)
- Aluguel if ever shown = MRLR only (omit in W1 panel)
- Vertical fixed: `academia`
- Map themes: **Claro + Escuro** sempre; usuário define (localStorage); 1ª visita fallback claro · Satélite no mesmo segmented
- Camadas UI W1 **igual print:** `Mapa de calor` + `Área de influência` (ambos opção) · sob influência: a pé \| carro · Legenda `Google Maps (N)`
- Influência visual = **OndeAbrir:** 3 isócronas 5/10/15 **reais** (ORS/Valhalla) + círculo azul da lente + legenda tempo inf. esquerdo · heatmap dados = W2
- Degustação: Turnstile + 1 grátis/email (same tables as site-agent analise) — do not invent second cap
- PDF / Nominatim default = **W2** (out)
- Commits **só se Marcelo pedir**
- Verifier BE: `c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest <path> -q --tb=short -x`
- Verifier FE: `npx tsc --noEmit` in `frontend/`
- Before pipeline/tool touch: `.agent/rules/conferencia-fontes-pipeline.md`

---

## File map

| File | Role |
|------|------|
| `tools/explorar_analise.py` | Pure build: lat/lng + lente → concorrentes + demografia + absorcao dict |
| `tools/test_explorar_analise.py` | TDD lente única + sem score + absorcao nested |
| `backend/routers/explorar.py` | `POST /api/explorar/analisar` + auth/degustação gates |
| `tests/test_explorar_api.py` | HTTP: 403 turnstile, quota, 200 shape |
| `api.py` (or router include) | Mount router |
| `frontend/src/routes/ExplorarPage.tsx` | Full-bleed map UI |
| `frontend/src/components/explorar/ExplorarControles.tsx` | Painel Controles = print (estilo + camadas + legenda) |
| `frontend/src/components/explorar/ExplorarMap.tsx` | Map + tiles + isócronas 5/10/15 + círculo lente + pins |
| `frontend/src/components/explorar/ExplorarBottomBar.tsx` | Academia + lente + Analisar |
| `frontend/src/components/explorar/ExplorarResultPanel.tsx` | Absorção + rivais |
| `frontend/src/hooks/useExplorarAnalise.ts` | POST + state |
| `frontend/src/router.tsx` | Public + authenticated routes |
| `frontend/src/lib/nav-items.ts` | Link “Explorar” when logged in |
| `docs/superpowers/previews/2026-08-07-explorar-w1.html` | Preview A/B + Controles mock — atualizar se layout mudar |
| `.superpowers/sdd/explorar-progress.md` | Ledger |

**Out of W1 data (UI already present):** isócrona ORS, heatmap demográfico real, PDF, Nominatim default, Voronoi-as-verdict, 23 business types.

---

# Wave W1a — Backend light analyze

### Task 1: `explorar_analise` pure function (TDD)

**Files:**
- Create: `tools/explorar_analise.py`
- Create: `tools/test_explorar_analise.py`

**Interfaces:**
```python
def run_explorar_analise(
    *,
    lat: float,
    lng: float,
    lente: Literal["500m", "1km", "bairro"],
    cidade: str | None = None,
    bairro: str | None = None,
    uf: str | None = None,
    area_candidato_m2: float = 1500.0,
    _concorrentes: list[dict] | None = None,  # test inject
    _setores: list[dict] | None = None,
    _ring: list[tuple[float, float]] | None = None,
) -> dict: ...
```

Return shape (minimal):
```python
{
  "lente": "1km",
  "base_espacial_label": str,  # vernáculo
  "pin": {"lat", "lng"},
  "concorrentes": [{"nome", "lat", "lng", "dist_m", "rating", "reviews"}],
  "absorcao_margem_fresca": dict,  # full attach output incl. voronoi_smoke if any
  "carimbo_base": str,
}
```

- [ ] **Step 1: Failing tests**

```python
def test_lente_1km_same_base_for_rivals_and_absorcao():
    from tools.explorar_analise import run_explorar_analise
    rivals = [
        {"nome": "A", "lat": -3.746, "lng": -38.489, "rating": 4.5, "reviews": 10},
        {"nome": "B", "lat": -3.747, "lng": -38.480, "rating": 4.0, "reviews": 5},
    ]
    out = run_explorar_analise(
        lat=-3.745, lng=-38.485, lente="1km",
        cidade="Fortaleza", bairro="Cocó", uf="CE",
        _concorrentes=rivals,
        _setores=[{"lat": -3.745, "lng": -38.485, "pessoas": 1000,
                   "h_25_39": 200, "m_25_39": 200, "h_40_59": 100, "m_40_59": 100,
                   "h_15_24": 50, "m_15_24": 50, "h_60_mais": 30, "m_60_mais": 30}],
    )
    assert out["lente"] == "1km"
    assert "score" not in out and "nota_0_10" not in out
    assert out["absorcao_margem_fresca"]["rotulo"] in ("fresco", "misto", "roubo")
    assert len(out["concorrentes"]) >= 1
    assert "1 km" in out["base_espacial_label"].lower() or "1km" in out["base_espacial_label"].lower()


def test_no_ondeabrir_score_keys():
    from tools.explorar_analise import run_explorar_analise
    out = run_explorar_analise(
        lat=-3.74, lng=-38.48, lente="500m",
        _concorrentes=[], _setores=[],
    )
    blob = str(out).lower()
    assert "oportunidade clara" not in blob
```

- [ ] **Step 2: Run — expect FAIL**

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tools/test_explorar_analise.py -q --tb=short -x
```

- [ ] **Step 3: Implement**
  - Resolve ring if `lente=="bairro"` via `resolver_bairro_poligono` (else None)
  - Filter rivals: haversine ≤ 500/1000 **or** point_in_ring
  - Build segmentos from `_setores` / load `carregar_setores_idade_sexo` with ring or bbox around pin+raio
  - Call `absorcao_margem_fresca` + try `compute_voronoi_smoke` via existing attach helpers (or inline sites_from_state-like)
  - Never add composite score

- [ ] **Step 4: Tests PASS**

- [ ] **Step 5: Commit only if Marcelo asks**

---

### Task 2: API router + degustação gate

**Files:**
- Create: `backend/routers/explorar.py`
- Create: `tests/test_explorar_api.py`
- Modify: `api.py` (include_router)

**Contract:**
```
POST /api/explorar/analisar
Body: {
  lat, lng, lente: "500m"|"1km"|"bairro",
  cidade?, bairro?, uf?,
  email?, turnstile_token?,  # required if anonymous
}
Auth: Bearer optional. If no user → Turnstile + email entitlement (reuse site_agent helpers).
```

- [ ] **Step 1: Failing tests** (TestClient)
  - anon without turnstile → 403
  - anon email already used → `quota_used` (or 200 with status field — match site-agent pattern)
  - authenticated mock → 200 with `absorcao_margem_fresca.rotulo`

- [ ] **Step 2: Implement router**
  - Reuse `_client_ip`, `verificar_turnstile`, `_email_ja_usou`, entitlement insert from `site_agent` (import helpers; do not duplicate tables)
  - Call `run_explorar_analise`
  - Log IP + lente (no PII beyond email on entitlement)

- [ ] **Step 3: Mount + pytest PASS**

---

# Wave W1b — Frontend map shell

### Task 3: Route + map chrome + Controles (paridade print)

**Files:**
- Create: `frontend/src/routes/ExplorarPage.tsx`
- Create: `frontend/src/components/explorar/ExplorarMap.tsx`
- Create: `frontend/src/components/explorar/ExplorarBottomBar.tsx`
- Create: `frontend/src/components/explorar/ExplorarControles.tsx`
- Modify: `frontend/src/router.tsx` — `/explorar` (auth layout) + public degustação
- Modify: `frontend/src/lib/nav-items.ts` — item Explorar

**Controles — espelho OndeAbrir (obrigatório):**

```
Controles [×]
├─ ESTILO DO MAPA
│   [Claro] [Escuro] [Satélite]     ← segmented 3, um ativo
├─ CAMADAS
│   ○ Mapa de calor                 ← opção sempre listada
│   ● Área de influência            ← opção sempre listada (highlight linha)
│       [🚶] [🚗]                   ← só se influência ativa
└─ LEGENDA
    ● Google Maps (N)
```

- State: `mapStyle: 'claro'|'escuro'|'satelite'`, `camada: 'calor'|'influencia'|null` (ou multi se print for exclusivo — print usa **um** highlight → tratar como radio entre calor e influência)
- Print mostra **seleção única** de camada (linha teal). Implementar **radio**: calor XOR influência. Ambos **sempre** no menu.
- Influência on → 3 polígonos 5/10/15 (a pé menor / carro maior) + círculo lente; a pé/carro já muda recorte no W1 (mock) e persiste pra ORS W2
- Calor on (W1) → toast/empty “Mapa de calor em breve” — **não** inventar heatmap

**Tiles:**
- Claro: CARTO light_all
- Escuro: CARTO dark_all
- Satélite: ESRI WorldImagery (ou disable + tooltip se política bloquear)

- [ ] **Step 1:** Page full-bleed + bottom bar; Analisar disabled without pin
- [ ] **Step 2:** Controles panel matches print structure; estilo switches tiles; camada influência draws circle; calor empty-state
- [ ] **Step 3:** `localStorage` keys: `explorar-map-style`, `explorar-camada`, `explorar-modo-desloc`
- [ ] **Step 4:** `npx tsc --noEmit`

**Geocode W1:** `POST /api/explorar/geocode` wrapping `geocode_endereco` (fold into Task 2 se faltar).

---

### Task 4: Analyze wire + panel

**Files:**
- Create: `frontend/src/hooks/useExplorarAnalise.ts`
- Create: `frontend/src/components/explorar/ExplorarResultPanel.tsx`
- Reuse: `AbsorcaoMargemFrescaCard`

- [ ] **Step 1:** On Analisar → POST; show loading; panel with Absorção + rival list + one-line base label
- [ ] **Step 2:** Plot rival markers (same N as list); Controles **LEGENDA** = `Google Maps (N)` (N sync com lista)
- [ ] **Step 3:** Degustação: collect email + Turnstile before first Analisar (mirror landing pattern)
- [ ] **Step 4:** `tsc --noEmit`

**Copy ban:** no “score”, no “oportunidade clara”.

---

### Task 5: Preview + Marcelo gate

**Files:**
- Create: `docs/superpowers/previews/2026-08-07-explorar-w1-claro.html` (or live route screenshot)
- Create: `.superpowers/sdd/explorar-progress.md`

- [ ] **Step 1:** Run local FE; open `/explorar` claro e escuro side-by-side
- [ ] **Step 2:** Smoke Cocó pin → expect rótulo **roubo**/disputa if data matches fixture world (or honest empty)
- [ ] **Step 3:** Marcelo picks **default theme**; update spec §9
- [ ] **Step 4:** Commit only if asked

---

## Self-review (plan)

- [x] W1 only — isochrone/PDF deferred  
- [x] No OndeAbrir score path  
- [x] Degustação reuses entitlement  
- [x] Dual map themes explicit  
- [x] Tests before implement per task  

---

## Execution handoff

Plan saved: `docs/superpowers/plans/2026-08-07-explorar-mapa-w1.md`

**1. Subagent-driven (recommended)** — dispatch per task with review between  
**2. Inline** — `executing-plans` in this session

Which way?
