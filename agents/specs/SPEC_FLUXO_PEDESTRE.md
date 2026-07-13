# SPEC_FLUXO_PEDESTRE.md

---
id: spec-fluxo-001
modulo: Fluxo Pedestre / Sintaxe Espacial
versao: 1.0
data: 2026-07-12
constitution: P-010 (carimbo obrigatório)
---

## 1. Responsabilidade

Calcular **fluxo estrutural de pedestres** (Natural Movement / Choice angular) a partir da malha viária OSM, sem sensores físicos. Entrega:

- `fluxo_score` 0–100 por candidato de imóvel (A1)
- GeoJSON de segmentos com `flow_score` 0–1 (mapa)
- Bloco `fluxo_pedestre` no relatório (A6)

Complementa (não substitui) `score_ancoragem` e `popular_times`.

## 2. Modelo matemático

### Custo angular (caminho P)

```
Cost(P) = Σ θ(e_i, e_{i+1})
```

θ = deflexão em radianos entre segmentos consecutivos no grafo dual.

### Choice (betweenness angular)

```
C_B(v) = Σ_{s≠t} σ_st(v) / σ_st
```

Caminhos minimizam soma de θ. Amostragem `k ≤ 500` para performance.

### Atratividade (MVP)

```
W_segmento = α·D_pop + β·D_emp + γ·I_transp
```

| Coef | Valor inicial | Fonte |
|------|---------------|-------|
| α | 0.33 | `censo_setor` IBGE 2022 (pop no entorno do segmento) |
| β | 0.33 | Overpass `shop`, `office`, `leisure=fitness_centre` |
| γ | 0.34 | Overpass `bus_station`, `subway_station`, `public_transport` |

### Flow score combinado

```
flow_raw = 0.5·Choice_norm + 0.3·Integration_norm + 0.2·POI_norm
FlowNorm = minmax(flow_raw) ∈ [0, 1]
fluxo_score = round(FlowNorm × 100)
```

### Calibração benchmark

Cocó/Fortaleza: OndeAbrir reporta **Fluxo 80/100**. Ordem de magnitude alvo para artéria estrutural (Av. Beira Mar, Dom Luís): `fluxo_score ≥ 70`.

## 3. Contrato JSON — candidato (A1)

```json
{
  "fluxo_score": 82,
  "fluxo_norm": 0.82,
  "fluxo_segmento": "Av. Beira Mar",
  "fluxo_confianca": "alta",
  "fluxo_carimbo": {
    "valor": 82,
    "base": "segmento mais próximo · raio 2000 m",
    "fonte": "OSM malha viária + IBGE Censo 2022 + Overpass POIs",
    "janela": "malha estática · censo 2022",
    "metodo": "angular segment analysis (Choice + Integration)"
  }
}
```

`fluxo_confianca`: `alta` | `media` | `baixa` | `indisponivel`

## 4. Contrato JSON — endpoint

`GET /api/relatorios/{id}/fluxo-pedestre?raio_m=2000`

```json
{
  "success": true,
  "confianca": "alta",
  "fluxo_score_candidato": 82,
  "carimbo": { "...": "..." },
  "statistics": { "total_segments": 245, "mean_flow_score": 0.42 },
  "geojson": { "type": "FeatureCollection", "features": [] },
  "attribution": "© OpenStreetMap contributors"
}
```

Falha OSM: `{ "success": false, "confianca": "indisponivel", "motivo": "..." }` — **nunca** scores sintéticos.

## 5. Integração pipeline

| Agente | Ação |
|--------|------|
| A1 | `enrich_candidato_fluxo()` após `score_ancoragem` nos top 10 |
| A6 | bloco `fluxo_pedestre` em `output_consolidado` + `generate_context_for_rag` no top candidato |
| API | cache Supabase `spatial_flow_cache` TTL 90d |

## 6. Regras de carimbo (P-010)

Todo número exibido ao usuário DEVE carregar `fluxo_carimbo` com `valor`, `base`, `fonte`, `janela`, `metodo`. UI bloqueia badge sem carimbo.

## 7. Dependências

`osmnx`, `networkx`, `geopandas`, `shapely` — ver `requirements.txt`.

## 8. Caso golden

Entrada: Cocó `lat=-3.743, lng=-38.487, radius=2000`

POIs: concorrentes do relatório (Smart Fit, Selfit, Fitway)

Assert: `mean_flow_score > 0.3`, top segmento com `flow_score > 0.6`, `fluxo_score` candidato âncora > candidato em rua local adjacente.
