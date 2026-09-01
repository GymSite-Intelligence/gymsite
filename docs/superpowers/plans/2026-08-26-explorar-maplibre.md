# Explorar MapLibre + Top Vias — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/explorar` uses MapLibre + CARTO vector (Positron / Dark Matter) and Esri satellite in-GL; honest empty heat; Top Vias overlay from a third button beside car — without blocking Analisar.

**Architecture:** Keep `ExplorarPage` analyze/isochrone flow. Replace tile engine in `ExplorarMap` with `react-map-gl/maplibre`. Pure `mapLibreStyle()` in `explorarIso.ts`. WebGL fail → existing pigeon (no CSS heat blob). Top Vias = separate `POST /api/explorar/top-vias` wrapping `top_vias_por_fluxo` (same A6 tool, cache), fetched only when influência + vias toggle + pin.

**Tech Stack:** `maplibre-gl`, `react-map-gl` (maplibre entry), FastAPI, `tools.fluxo_pedestre_tools.top_vias_por_fluxo`, React 18, `npx tsc --noEmit`, `.venv` pytest.

**Spec:** `docs/superpowers/specs/2026-08-26-explorar-maplibre-design.md` (wave 1 + 1b). Wave 2 PDF/tela relatório **out**.

## Global Constraints

- No score 0–10 · no fake heat (no radial CSS on the pin)
- No CARTO LDS `calculate_isolines` · isochrones stay ORS `POST /api/explorar/isocronas`
- No Google Maps JS on `/explorar` · do not edit `GoogleMapOceano.tsx`
- Chrome panels stay GymSite tokens (`explorarChrome`); map tiles user-chosen
- Candidate pin fill = `GYMSITE_PALETTE.lime` (`#84cc01`); rivals = destructive red for Maps legend
- Pé/carro = radio `ModoDesloc`; Vias = independent boolean, `localStorage` key `explorar-top-vias`
- Vias row only when `camada === 'influencia'`
- Analisar must not await osmnx
- `top_vias` numbers keep carimbo from the tool; fail-soft empty overlay
- Commits **only if Marcelo asks**
- Verifier BE: `c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest <path> -q --tb=short -x`
- Verifier FE: `npx tsc --noEmit` in `frontend/`
- UI change → preview `docs/superpowers/previews/` + open in browser (preview-aprovacao)

---

## File map

| File | Role |
|------|------|
| `frontend/package.json` | add `maplibre-gl`, `react-map-gl` |
| `frontend/src/components/explorar/explorarIso.ts` | `mapLibreStyle`, `topViasToFeatureCollection`; keep `tileProvider` for pigeon fallback |
| `frontend/src/components/explorar/explorarIso.test.ts` | style URLs + vias GeoJSON |
| `frontend/src/components/explorar/ExplorarMap.tsx` | MapLibre primary + pigeon fallback; no heat blob |
| `frontend/src/components/explorar/ExplorarControles.tsx` | `grid-cols-3` + Route button |
| `frontend/src/hooks/useExplorarTopVias.ts` | POST top-vias query |
| `frontend/src/routes/ExplorarPage.tsx` | `viasOn` state, pass GeoJSON/loading into map + controles |
| `backend/routers/explorar.py` | `POST /api/explorar/top-vias` |
| `tests/test_explorar_top_vias_api.py` | HTTP shape + fail-soft |
| `docs/superpowers/previews/2026-08-26-explorar-maplibre.html` | static chrome mock of 3 buttons (mapa GL = rota local) |

---

### Task 1: `mapLibreStyle` + `topViasToFeatureCollection` (TDD)

**Files:**
- Modify: `frontend/src/components/explorar/explorarIso.ts`
- Modify: `frontend/src/components/explorar/explorarIso.test.ts`

**Interfaces:**
- Consumes: existing `MapStyle`
- Produces:
  - `mapLibreStyle(style: MapStyle): string | Record<string, unknown>`
  - `topViasToFeatureCollection(vias: { nome_via?: string; fluxo_score?: number; coords?: [number, number][] }[]): GeoJSON FeatureCollection`

- [ ] **Step 1: Write failing assertions** at end of `explorarIso.test.ts`:

```ts
import { mapLibreStyle, topViasToFeatureCollection } from './explorarIso.ts'

const claro = mapLibreStyle('claro')
assert.equal(typeof claro, 'string')
assert.ok(String(claro).includes('positron-gl-style'))
const escuro = mapLibreStyle('escuro')
assert.ok(String(escuro).includes('dark-matter-gl-style'))
const sat = mapLibreStyle('satelite')
assert.equal(typeof sat, 'object')
assert.ok(JSON.stringify(sat).includes('World_Imagery'))

const fc = topViasToFeatureCollection([
  { nome_via: 'Rua A', fluxo_score: 90, coords: [[-38.48, -3.74], [-38.49, -3.75]] },
  { nome_via: 'Sem linha', fluxo_score: 10 },
])
assert.equal(fc.features.length, 1)
assert.equal(fc.features[0].geometry.type, 'LineString')
```

- [ ] **Step 2: Run to fail**

```bash
cd frontend && node --experimental-strip-types src/components/explorar/explorarIso.test.ts
```

Expected: FAIL (`mapLibreStyle` / `topViasToFeatureCollection` not exported).

- [ ] **Step 3: Implement in `explorarIso.ts`**

```ts
export const CARTO_POSITRON_STYLE =
  'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'
export const CARTO_DARK_MATTER_STYLE =
  'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json'

const ESRI_SAT_STYLE = {
  version: 8,
  sources: {
    esri: {
      type: 'raster',
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      ],
      tileSize: 256,
      attribution: '© Esri',
    },
  },
  layers: [{ id: 'esri', type: 'raster', source: 'esri' }],
} as const

export function mapLibreStyle(style: MapStyle): string | typeof ESRI_SAT_STYLE {
  if (style === 'escuro') return CARTO_DARK_MATTER_STYLE
  if (style === 'satelite') return ESRI_SAT_STYLE
  return CARTO_POSITRON_STYLE
}

export function topViasToFeatureCollection(
  vias: { nome_via?: string; fluxo_score?: number; coords?: [number, number][] }[],
) {
  return {
    type: 'FeatureCollection' as const,
    features: vias
      .filter((v) => Array.isArray(v.coords) && v.coords.length >= 2)
      .map((v, i) => ({
        type: 'Feature' as const,
        properties: {
          nome: v.nome_via ?? '',
          fluxo: v.fluxo_score ?? 0,
          rank: i,
        },
        geometry: { type: 'LineString' as const, coordinates: v.coords! },
      })),
  }
}
```

Note: `coords` from backend are `[lon, lat]` (see `tools/vias_geometry_tools.py`). Do not swap.

- [ ] **Step 4: Re-run test** — Expected: PASS (`explorarIso camada ok` still prints).

- [ ] **Step 5: Commit** — skip unless Marcelo asked.

---

### Task 2: Install MapLibre deps

**Files:**
- Modify: `frontend/package.json`, `frontend/package-lock.json`

**Interfaces:**
- Produces: packages `maplibre-gl` and `react-map-gl` (import from `react-map-gl/maplibre`)

- [ ] **Step 1:** In `frontend/`:

```bash
npm install maplibre-gl react-map-gl
```

- [ ] **Step 2:** Confirm `frontend/package.json` has both. No Google Maps packages added.

- [ ] **Step 3: Commit** — skip unless Marcelo asked.

---

### Task 3: `ExplorarMap` MapLibre (iso + lente + pins + popup; no heat blob)

**Files:**
- Modify: `frontend/src/components/explorar/ExplorarMap.tsx`

**Interfaces:**
- Consumes: current props; `mapLibreStyle`, `influenceFeatureCollection`, `ISO_STYLE`, `GYMSITE_PALETTE`, `CARTO_ATTRIBUTION`
- Produces: same callbacks; optional later props `viasFc` / `viasOn` (add in Task 7 if not stubbed as `viasFc = null`)

Add import `maplibre-gl/dist/maplibre-gl.css` once (this file or `ExplorarPage`).

- [ ] **Step 1:** Delete the `heat && pin` Overlay radial-gradient block entirely. `camada === 'calor'` paints nothing on the map.

- [ ] **Step 2:** Detect WebGL:

```ts
import maplibregl from 'maplibre-gl'

const glOk = typeof window !== 'undefined' && maplibregl.supported()
```

If `!glOk`, render **existing** pigeon `Map` (Task 4 also strips blob). If `glOk`, render:

```tsx
import Map, { Source, Layer, Marker, Popup } from 'react-map-gl/maplibre'

<Map
  mapLib={maplibregl}
  style={{ width: '100%', height: '100%' }}
  mapStyle={mapLibreStyle(mapStyle)}
  longitude={center[1]}
  latitude={center[0]}
  zoom={zoom}
  onMoveEnd={(e) => onZoom(e.viewState.zoom)}
  onClick={(e) => {
    setActiveRival(null)
    onClickMap(e.lngLat.lat, e.lngLat.lng)
  }}
  attributionControl={false}
>
  {/* Source isoData GeoJSON fill+line layers keyed m15,m10,m5,lente */}
  {/* Source rivals as GeoJSON points; cluster: true */}
  {/* Marker pin lime */}
</Map>
```

Layer paint (iso): reuse `ISO_STYLE` fills; lente stroke `#2563eb`, fill none. `pointer-events: none` on iso/lente.

Rivals: `unclustered-point` circle color `#ef4444`; selected lime. Cluster: `circle-color` `#ef4444`, `text-field` `{point_count}`. Click unclustered → `setActiveRival`. Popup: `nome`, `endereco`, `rating`, `reviews`.

Candidate: `Marker` with `GYMSITE_PALETTE.lime`, white border, `aria-label="Ponto candidato"`.

Attribution: MapLibre `AttributionControl` compact or overlay span `CARTO_ATTRIBUTION` (+ Esri when satelite).

Controlled view: if `react-map-gl` fights `center`/`zoom` from parent, use `viewState` + `onMove` matching current `ExplorarPage` lock (`zoomLock`). Do **not** change page fly-to behavior besides engine.

- [ ] **Step 3:** `npx tsc --noEmit` in `frontend/`. Expected: 0 errors.

- [ ] **Step 4: Commit** — skip unless Marcelo asked.

---

### Task 4: Pigeon fallback — no blob

**Files:**
- Modify: `frontend/src/components/explorar/ExplorarMap.tsx` (pigeon branch only)

**Interfaces:**
- Consumes: `tileProvider`, `influenceFeatureCollection` (unchanged)

- [ ] **Step 1:** In pigeon branch, keep GeoJSON iso + Overlay pins/popup. Confirm no `radial-gradient` / `size-90` heat overlay remains in the file (`rg radial-gradient ExplorarMap.tsx` = no matches).

- [ ] **Step 2:** If `!glOk`, show a one-line `sr-only` or small muted text in chrome is **optional**; spec says short recado — add `p` visually hidden or toast once is enough: "Mapa simplificado neste aparelho."

- [ ] **Step 3: Commit** — skip unless Marcelo asked.

---

### Task 5: `POST /api/explorar/top-vias` (TDD)

**Files:**
- Modify: `backend/routers/explorar.py`
- Create: `tests/test_explorar_top_vias_api.py`

**Interfaces:**
- Consumes: `top_vias_por_fluxo(lat, lng, top_n=5, radius_m=2000, competidores=None, bairro="")`
- Produces: JSON passthrough `{ status, top_vias, confianca, motivo? }` — **omit** `mapa_svg` / `mapa_png` in API response (strip in router) so payload stays small.

```python
class ExplorarTopViasInput(BaseModel):
    lat: float
    lng: float
    bairro: Optional[str] = Field(default=None, max_length=120)
```

```python
@router.post("/top-vias")
async def explorar_top_vias(data: ExplorarTopViasInput) -> dict[str, Any]:
    from tools.fluxo_pedestre_tools import top_vias_por_fluxo
    raw = top_vias_por_fluxo(data.lat, data.lng, top_n=5, radius_m=2000, bairro=data.bairro or "")
    if not isinstance(raw, dict):
        return {"status": "indisponivel", "top_vias": [], "confianca": "indisponivel"}
    out = {k: v for k, v in raw.items() if k not in ("mapa_svg", "mapa_png")}
    return out
```

Same auth as `/isocronas` (none). Fail-soft: tool never raises to 500 — wrap `except Exception` → `status: indisponivel`.

- [ ] **Step 1: Failing test** `tests/test_explorar_top_vias_api.py`:

```python
from fastapi.testclient import TestClient
from api import app

def test_top_vias_ok_shape(monkeypatch):
    def fake(lat, lng, **kwargs):
        return {
            "status": "ok",
            "top_vias": [{"nome_via": "Rua X", "fluxo_score": 80, "coords": [[-38.4, -3.7], [-38.41, -3.71]]}],
            "confianca": "alta",
            "mapa_png": "SHOULD_STRIP",
        }
    monkeypatch.setattr("tools.fluxo_pedestre_tools.top_vias_por_fluxo", fake)
    c = TestClient(app)
    r = c.post("/api/explorar/top-vias", json={"lat": -3.74, "lng": -38.48})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "mapa_png" not in body
    assert body["top_vias"][0]["nome_via"] == "Rua X"

def test_top_vias_fail_soft(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("osmnx down")
    monkeypatch.setattr("tools.fluxo_pedestre_tools.top_vias_por_fluxo", boom)
    c = TestClient(app)
    r = c.post("/api/explorar/top-vias", json={"lat": -3.74, "lng": -38.48})
    assert r.status_code == 200
    assert r.json()["status"] == "indisponivel"
    assert r.json()["top_vias"] == []
```

Patch the **router import path** if the endpoint imports inside the function — monkeypatch `backend.routers.explorar.top_vias_por_fluxo` after binding, or patch where used. If import is inside handler, `monkeypatch.setattr("tools.fluxo_pedestre_tools.top_vias_por_fluxo", ...)`.

- [ ] **Step 2:** Run test — Expected FAIL (404).

```bash
c:\Users\marce\gymsite\.venv\Scripts\python.exe -m pytest tests/test_explorar_top_vias_api.py -q --tb=short -x
```

- [ ] **Step 3:** Implement route. Re-run — Expected PASS.

- [ ] **Step 4: Commit** — skip unless Marcelo asked.

---

### Task 6: Hook `useExplorarTopVias`

**Files:**
- Create: `frontend/src/hooks/useExplorarTopVias.ts`

**Interfaces:**
- Consumes: `API_BASE` (same as `useExplorarIsocronas`)
- Produces:

```ts
export function useExplorarTopVias(
  pin: { lat: number; lng: number } | null,
  bairro: string | undefined,
  enabled: boolean,
)
```

`enabled` = influência && viasOn && pin. `queryKey`: `['explorar-top-vias', lat, lng, bairro]`. `staleTime: 30 * 60_000`. `retry: 1`. `meta: { silent: true }`. On HTTP error treat as `{ status: 'indisponivel', top_vias: [] }` in `queryFn` catch — do not throw to a blocking toast on Analisar.

- [ ] **Step 1:** Implement `queryFn` POST `/api/explorar/top-vias` JSON `{ lat, lng, bairro }`.

- [ ] **Step 2:** `npx tsc --noEmit`.

- [ ] **Step 3: Commit** — skip unless Marcelo asked.

---

### Task 7: Controles 3rd button + wire page + map lines

**Files:**
- Modify: `frontend/src/components/explorar/ExplorarControles.tsx`
- Modify: `frontend/src/routes/ExplorarPage.tsx`
- Modify: `frontend/src/components/explorar/ExplorarMap.tsx`
- Modify: `frontend/src/components/explorar/ExplorarResultPanel.tsx` (optional 3-name list if `resultOpen` and vias ok)

**Interfaces:**
- Consumes: `useExplorarTopVias`, `topViasToFeatureCollection`
- Produces: `viasOn: boolean`, `onVias: () => void`, `viasPending: boolean`

`ExplorarControles` extra props:

```ts
viasOn: boolean
viasPending: boolean
onVias: () => void
```

Change inner grid `grid-cols-2` → `grid-cols-3`. Third button: `Route` from `lucide-react`, `aria-label="Top vias"`, `title="Vias de maior fluxo"`. Selected = `viasOn` lime (same classes as modo). Disabled visual: `opacity-60` when `viasPending`. Click only toggles `viasOn` — does not change `modo`.

`ExplorarPage`:

```ts
const [viasOn, setViasOn] = useState(() =>
  readLs('explorar-top-vias', 'off', ['on', 'off']) === 'on',
)
```

`writeLs` on toggle. `useExplorarTopVias(pin, lugar.bairro, camada === 'influencia' && viasOn)`.

Pass `viasFc={data?.status === 'ok' ? topViasToFeatureCollection(data.top_vias) : { type:'FeatureCollection', features:[] }}` into `ExplorarMap`.

MapLibre: Source `explorar-vias` LineString; line-color interpolate by `fluxo` or rank (top = `#ea580c` / red-orange like PDF). `visibility` none unless `camada === 'influencia' && viasOn`.

Pigeon fallback: skip line overlay if too costly; still OK to skip lines in pigeon (spec: GL primary). Optional: skip.

Result panel: if `viasOn && data?.status === 'ok'`, list top 3 `nome_via` + `fluxo_score` + one-line carimbo from first via `fluxo_carimbo` if present. If `indisponivel`, no fake ranks.

- [ ] **Step 1:** Wire as above.

- [ ] **Step 2:** `npx tsc --noEmit`.

- [ ] **Step 3: Commit** — skip unless Marcelo asked.

---

### Task 8: Preview + manual check

**Files:**
- Create: `docs/superpowers/previews/2026-08-26-explorar-maplibre.html`

**Interfaces:** none

- [ ] **Step 1:** HTML mock of Controles: 3 style buttons + calor + influência + **3 icon buttons** (person, car, route) lime on route. Caption: “fileira influência — Vias não é modo de isócrona”.

- [ ] **Step 2:** Open preview in browser. Open `/explorar` locally: WebGL map Positron; toggle escuro Dark Matter; satélite Esri; influência isochrones; click Vias (cache may wait); Analisar still returns absorção without waiting vias.

- [ ] **Step 3:** Confirm `GoogleMapOceano.tsx` git-clean.

- [ ] **Step 4: Commit** — skip unless Marcelo asked.

---

## Spec coverage (self-review)

| Spec item | Task |
|-----------|------|
| MapLibre + Positron/Dark Matter | 1, 2, 3 |
| Esri inside MapLibre | 1, 3 |
| Same analyze/isochrone contract | 3 (no API change analisar) |
| No heat blob | 3, 4 |
| Pins lime/red, cluster, popup | 3 |
| Fallback pigeon | 3, 4 |
| No Google / no LDS isoline | constraints + Task 2 |
| Vias button beside car | 7 |
| Vias not in Analisar | 5–7 (separate route) |
| Strip PNG from API | 5 |
| Preview | 8 |
| Wave 2 PDF | **out** (no task) |

Placeholder scan: no TBD. Types: `viasOn` boolean; `mapLibreStyle` return `string | style object`; coords lon-lat.
