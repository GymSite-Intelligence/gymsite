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
   - (opcional) Places API, Street View Static API, Distance Matrix API
4. Ou em dev: **Don't restrict key**.
5. [Billing](https://console.cloud.google.com/billing) ativo no projeto.
6. Ative na [Library](https://console.cloud.google.com/apis/library):
   - [Geocoding API](https://console.cloud.google.com/apis/library/geocoding-backend.googleapis.com)
   - [Places API (New)](https://console.cloud.google.com/apis/library/places.googleapis.com)
7. Aguarde ~5 min e valide:

```bash
python tools/maps_health_check.py
curl https://gymsite-api.vectracargo.com.br/health/maps
```

## Fallback automático (já no código)

Com `MAPS_FALLBACK_ENABLED=1` (padrão):

| Função | Fallback |
|--------|----------|
| Geocode | [Nominatim](https://nominatim.org/) (OSM) |
| Academias no raio | [Overpass](https://overpass-api.de/) (OSM) |

O pipeline **não fica zerado** enquanto a chave Google não for corrigida. Reviews/horários detalhados do Places continuam limitados.

## Deploy

Após alterar `.env`:

```bash
docker compose build api
docker compose up -d api
```
