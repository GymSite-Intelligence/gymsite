# Google Maps API — configuração e fallback

## Sintoma

- `Geocoding falhou: REQUEST_DENIED`
- `Places API ... are blocked` / `API key is not authorized`

## Correção definitiva (Google Cloud)

1. Abra [Credentials](https://console.cloud.google.com/apis/credentials).
2. Edite a chave em `GOOGLE_MAPS_API_KEY` (não use chave restrita só a **Generative Language API**).
3. **API restrictions** → selecione:
   - Geocoding API
   - Places API (New)
   - Distance Matrix API
   - Maps JavaScript API (heatmap em `/mapa` via deck.gl — **não** exige Maps Visualization)
   - (opcional) Street View Static API
4. Ou em dev: **Don't restrict key**.
5. [Billing](https://console.cloud.google.com/billing) ativo no projeto.
6. Ative na [Library](https://console.cloud.google.com/apis/library):
   - [Geocoding API](https://console.cloud.google.com/apis/library/geocoding-backend.googleapis.com)
   - [Places API (New)](https://console.cloud.google.com/apis/library/places.googleapis.com)
7. Aguarde ~5 min e valide:

```bash
python tools/maps_health_check.py
curl https://gymsite-api.vectracargo.com.br/health/maps
curl http://localhost:8000/api/config/maps-js
```

**Mapa /heatmap:** o frontend carrega a chave via `GET /api/config/maps-js` (nunca no bundle). Em dev, `npm run dev` + `uvicorn api:app --port 8000` com `VITE_API_BASE=http://localhost:8000`.

### Heatmap (deprecação Maps Visualization, maio/2026)

A partir da **v3.65** do Maps JavaScript API, `google.maps.visualization.HeatmapLayer` foi descontinuado. Este projeto usa **[deck.gl `HeatmapLayer`](https://deck.gl/docs/api-reference/aggregation-layers/heatmap-layer)** com [`@deck.gl/google-maps`](https://deck.gl/docs/api-reference/google-maps/overview) (`GoogleMapsOverlay`).

- **APIs necessárias:** apenas **Maps JavaScript API** (mesma chave e restrições de referrer HTTP do mapa).
- **Não ative** Maps Visualization só por causa do heatmap.
- Paleta e pesos: `frontend/src/lib/heatmap-weight.ts` (`pinHeatmapWeight`, `oceanoDeckColorRange`).
- Verificação: `/mapa` → lente Mercado (A9) → **Calor** ou **Ambos**; fallback pigeon inalterado.

## Fallback automático (já no código)

`MAPS_FALLBACK_ENABLED` default no código = **`0` (off)** — ver `tools/maps_fallback.py`.  
Prod pode ligar com `MAPS_FALLBACK_ENABLED=1` (ex.: `.env.production.example`).

Com fallback **ligado** (`1` / `true` / `yes`):

| Função | Fallback |
|--------|----------|
| Geocode | [Nominatim](https://nominatim.org/) (OSM) |
| Academias no raio | [Overpass](https://overpass-api.de/) (OSM) |

Com Google Maps OK e fallback off, Places/geocode Google seguem no caminho principal. Reviews/horários detalhados do Places continuam limitados se a chave falhar sem fallback.

## Deploy

Após alterar `.env`:

```bash
docker compose build api
docker compose up -d api
```
