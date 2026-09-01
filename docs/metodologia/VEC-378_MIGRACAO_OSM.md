# VEC-378 — Camada OSM (Nominatim / Overpass / ORS|Valhalla)

> Objetivo: geo determinístico via OpenStreetMap (geocode, POIs/âncoras, isócronas),
> sem billing Google Maps Platform no caminho crítico.
> Concorrentes (nome/rating/review) continuam em **SearchAPI `google_maps`** —
> mesma mistura Google+OSM que o OndeAbrir declara; não migrar qualidade comercial.

## Status (2026-08-26)

| Fase | Estado | Notas |
|------|--------|--------|
| 0 Baseline custo Google | **Cancelada / N/A** | GCP Maps billing fora do caminho; DM off (`DISTANCE_MATRIX_ENABLED`) |
| 1 Geocode Nominatim | **Parcial ✅** | `nominatim_geocoder.py` + `maps_fallback`; sem flag `GEOCODER=` canônica |
| 2 POIs/âncoras Overpass | **✅ Entregue** | `tools/osm_pois.py` → polos + top vias; `space_syntax.fetch_pois_from_overpass` unificado |
| 3 Isócronas | **Parcial ✅** | `osm_isocronas.py` no Explorar; falta no relatório/PDF A1 |
| 4 Cache central + flags | **Aberto** | Cache disco em `osm_pois`; sem tabela `osm_cache` / flags unificadas |
| Self-host B | **Aberto** | Públicos + rate limit; opcional |

## 1. Divisão de fontes (atual)

| Necessidade | Fonte canônica | Fallback |
|---|---|---|
| Endereço → coordenada | Nominatim | — (Google geo não é caminho crítico) |
| POIs/âncoras (parking, escola, hospital, bus, shop) | Overpass (`osm_pois`) | lista vazia fail-soft |
| Distâncias ponto↔polo | Haversine (`calcular_distancia_km`) | ORS matrix (Fase 3b, aberto) |
| Área de influência 5/10/15 min | ORS / Valhalla (`osm_isocronas`) | Explorar só; PDF aberto |
| Fluxo pedestre | OSMnx + sintaxe espacial (+ POIs Overpass) | — |
| Concorrentes nome/rating/review | SearchAPI `google_maps` | Places / Overpass fitness |
| Street View imóvel | Google (se houver key) | omitir |

## 2. Arquitetura (código real, não o esboço antigo)

```
tools/nominatim_geocoder.py   # Fase 1
tools/maps_fallback.py        # Nominatim + Overpass fitness
tools/osm_pois.py             # Fase 2 — âncoras por categoria
tools/osm_isocronas.py        # Fase 3 — isócronas Explorar
tools/space_syntax.py         # fluxo; fetch_pois_from_overpass = wrapper osm_pois
tools/anchoring_tools.py      # score_ancoragem consome polos (agora OSM-first)
```

Cache Fase 2: `tools/cache/osm_pois/*.json` (TTL ~30 dias, chave lat/lng/raio/cats).

## 3. Fase 2 — escopo (paridade OndeAbrir “ponto físico”)

OndeAbrir mostra: estacionamentos, âncoras com distância, fatores do ponto.
GymSite Fecha o buraco com Overpass:

| Categoria | Tags OSM | Uso produto |
|-----------|----------|-------------|
| `parking` | `amenity=parking` | contagem + proximidade |
| `school` | `amenity=school` | âncora fluxo |
| `university` | `amenity=university` | âncora fluxo |
| `hospital` | `amenity=hospital` \| `clinic` | âncora |
| `bus_station` | `amenity=bus_station` \| `public_transport=*` \| `railway=station` | transporte |
| `supermarket` | `shop=supermarket` \| `mall` \| `department_store` | comércio âncora |

API:

- `osm_pois(lat, lng, raio_m=1000, categorias=None) -> {pois, contagens, fonte, carimbo}`
- `polos_para_ancoragem(...)` → shape compatível com `calcular_score_ancoragem`
- Fail-soft: Overpass down → `{pois: [], status: indisponivel}`

**Não** inclui `leisure=fitness_centre` como “âncora de mercado” — isso é concorrência (SearchAPI).

## 4. Fases restantes

- **3b** — `osm_matrix` + isócronas no PDF/A6 (área de influência).
- **4** — flags `POIS_SOURCE` / cache Postgres.
- **Self-host** — só se rate limit públicos morder prod.

## 5. Impacto

- Âncoras/estacionamentos sem Places Nearby pago.
- Score ancoragem deixa de depender de Text Search genérico (quando OSM hit).
- Atribuição ODbL obrigatória: “© OpenStreetMap contributors” em mapas/seções geo.

## 6. Riscos

- Cobertura OSM irregular em cidade pequena → contagens baixas (honesto) ≠ inventar POI.
- Rate limit Overpass → cache disco + User-Agent identificado.
- Atacadista de marca (Assaí etc.) pode faltar no OSM → `buscar_polos_geradores` ainda pode complementar via texto se OSM vazio em `supermarket`.

## 7. Integração

- BQ/IBGE: demografia/renda/CNO intactos.
- SearchAPI: só concorrentes + listings.
- Consultor: isócronas já no Explorar; tool relatório depois (Fase 3b).
