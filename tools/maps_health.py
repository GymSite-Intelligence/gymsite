"""
Diagnóstico da Google Maps Platform API key (Geocoding + Places + extensões).
"""
from __future__ import annotations

import httpx

from tools.google_maps_key import get_google_maps_api_key

_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
_PLACES_SEARCH = "https://places.googleapis.com/v1/places:searchText"
def check_google_maps() -> dict:
    """
    Testa Geocoding, Places (New), Street View metadata e Area Insights.
    Não grava cache.
    """
    key = get_google_maps_api_key()
    base = {
        "configured": bool(key),
        "key_hint": f"{key[:8]}..." if len(key) > 8 else None,
        "ok": False,
        "geocoding": {},
        "places_new": {},
        "street_view": {},
        "area_insights": {},
        "remediation": [],
    }
    if not key:
        base["remediation"] = [
            "Defina GOOGLE_MAPS_API_KEY no .env (raiz) e reinicie a API Docker.",
            "Não reutilize chave só de Gemini sem habilitar Maps APIs no mesmo projeto.",
        ]
        return base

    base["remediation"] = [
        "API restrictions: Geocoding, Places (New), Street View Static, Distance Matrix, Area Insights.",
        "MAPS_FALLBACK_ENABLED=0 (padrão) para priorizar Google; =1 só se quiser OSM em falha.",
    ]

    try:
        with httpx.Client(timeout=12) as c:
            geo = c.get(
                _GEOCODE_URL,
                params={
                    "address": "Meireles, Fortaleza, CE, Brasil",
                    "key": key,
                    "region": "BR",
                },
            ).json()
        gstatus = geo.get("status")
        base["geocoding"] = {
            "ok": gstatus == "OK",
            "status": gstatus,
            "message": geo.get("error_message"),
        }
    except Exception as exc:
        base["geocoding"] = {"ok": False, "status": "EXCEPTION", "message": str(exc)}

    try:
        with httpx.Client(timeout=12) as c:
            pr = c.post(
                _PLACES_SEARCH,
                json={"textQuery": "academia Fortaleza", "maxResultCount": 1},
                headers={
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": key,
                    "X-Goog-FieldMask": "places.displayName",
                },
            )
        if pr.status_code == 200:
            base["places_new"] = {"ok": True, "status": pr.status_code}
        else:
            err = (
                pr.json().get("error", {})
                if pr.headers.get("content-type", "").startswith("application/json")
                else {}
            )
            base["places_new"] = {
                "ok": False,
                "status": pr.status_code,
                "message": err.get("message") or pr.text[:200],
            }
    except Exception as exc:
        base["places_new"] = {"ok": False, "status": "EXCEPTION", "message": str(exc)}

    try:
        with httpx.Client(timeout=15) as c:
            # Metadata API pode estar restrita na chave; valida imagem Static.
            img = c.get(
                "https://maps.googleapis.com/maps/api/streetview",
                params={
                    "size": "200x120",
                    "location": "-3.724,-38.490",
                    "fov": 90,
                    "key": key,
                },
            )
        ctype = (img.headers.get("content-type") or "").lower()
        base["street_view"] = {
            "ok": img.status_code == 200 and "image" in ctype,
            "status": img.status_code,
            "message": None if img.status_code == 200 else img.text[:120],
        }
    except Exception as exc:
        base["street_view"] = {"ok": False, "status": "EXCEPTION", "message": str(exc)}

    try:
        from tools.places_aggregate_tools import compute_insight_count_circle

        agg = compute_insight_count_circle(
            latitude=-3.724,
            longitude=-38.490,
            radius_meters=3000,
            included_types=["gym", "fitness_center"],
        )
        base["area_insights"] = {
            "ok": "erro" not in agg,
            "count": agg.get("count"),
            "message": agg.get("erro"),
        }
    except Exception as exc:
        base["area_insights"] = {"ok": False, "message": str(exc)}

    # Street View é desejável mas não bloqueia pipeline (proxy pode servir 502).
    base["ok"] = bool(
        base.get("geocoding", {}).get("ok")
        and base.get("places_new", {}).get("ok")
        and base.get("area_insights", {}).get("ok")
    )
    base["street_view_optional"] = bool(base.get("street_view", {}).get("ok"))
    return base
