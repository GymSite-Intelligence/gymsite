"""
tools/places_aggregate_tools.py

Wrapper pequeno para Places Aggregate API (Area Insights).

Uso principal no GymSite:
  - obter contagens agregadas de tipos (ex: gym) num raio do bairro alvo
  - alimentar score competitivo com "densidade real" (não limitada ao maxResultCount do Nearby)
"""

from __future__ import annotations

import httpx

from tools.google_maps_key import get_google_maps_api_key


_AREA_INSIGHTS_BASE = "https://areainsights.googleapis.com/v1:computeInsights"


def compute_insight_count_circle(
    *,
    latitude: float,
    longitude: float,
    radius_meters: int,
    included_types: list[str],
    min_rating: float | None = None,
    max_rating: float | None = None,
    operating_status: list[str] | None = None,
    price_levels: list[str] | None = None,
    timeout_seconds: float = 15.0,
) -> dict:
    """
    Chama Places Aggregate API retornando INSIGHT_COUNT em círculo.

    Retorno:
      - {"count": int, "raw": {...}} em sucesso
      - {"erro": "..."} em falha (nunca levanta)
    """
    api_key = (get_google_maps_api_key() or "").strip()
    if not api_key:
        return {"erro": "GOOGLE_MAPS_API_KEY ausente"}
    if not included_types:
        return {"erro": "included_types vazio"}
    if radius_meters <= 0:
        return {"erro": "radius_meters inválido"}

    filt: dict = {
        "locationFilter": {
            "circle": {
                # Importante: no REST, Circle usa `latLng` direto (não `center`).
                # Ref: examples / reference do Places Aggregate.
                "latLng": {"latitude": float(latitude), "longitude": float(longitude)},
                "radius": float(radius_meters),
            }
        },
        "typeFilter": {"includedTypes": included_types},
    }

    # Default do serviço: se qualquer filtro opcional for usado, é recomendado
    # explicitar operatingStatus. Mantemos o default do backend quando None.
    if operating_status:
        filt["operatingStatus"] = operating_status
    if price_levels:
        filt["priceLevels"] = price_levels
    if min_rating is not None or max_rating is not None:
        rf: dict = {}
        if min_rating is not None:
            rf["minRating"] = float(min_rating)
        if max_rating is not None:
            rf["maxRating"] = float(max_rating)
        filt["ratingFilter"] = rf

    body = {"insights": ["INSIGHT_COUNT"], "filter": filt}
    headers = {"X-Goog-Api-Key": api_key, "Content-Type": "application/json"}

    try:
        # Rastreia o custo (areaInsights = SKU places_aggregate). Antes ZERO track →
        # ~R$37/dia invisível no /custos. Agora aparece se religado.
        from tools.api_cost_tracker import track_api_call

        with track_api_call("places_aggregate", "places_aggregate", 1):
            with httpx.Client(timeout=timeout_seconds) as c:
                resp = c.post(_AREA_INSIGHTS_BASE, json=body, headers=headers)
        if resp.status_code != 200:
            return {"erro": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        data = resp.json() if resp.content else {}
        raw_count = data.get("count")
        try:
            count_int = int(raw_count) if raw_count is not None else 0
        except (TypeError, ValueError):
            count_int = 0
        return {"count": count_int, "raw": data}
    except Exception as exc:
        return {"erro": f"Places Aggregate falhou: {type(exc).__name__}: {exc}"}

