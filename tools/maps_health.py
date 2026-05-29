"""
Diagnóstico da Google Maps Platform API key (Geocoding + Places New).
"""
from __future__ import annotations

import httpx

from tools.google_maps_key import get_google_maps_api_key

_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
_PLACES_SEARCH = "https://places.googleapis.com/v1/places:searchText"


def check_google_maps() -> dict:
    """
    Testa Geocoding e Places API (New). Não grava cache.
    Retorna status + passos de correção no Cloud Console.
    """
    key = get_google_maps_api_key()
    base = {
        "configured": bool(key),
        "key_hint": f"{key[:8]}..." if len(key) > 8 else None,
        "ok": False,
        "geocoding": {},
        "places_new": {},
        "remediation": [],
    }
    if not key:
        base["remediation"] = [
            "Defina GOOGLE_MAPS_API_KEY no .env (raiz) e reinicie a API Docker.",
            "Não reutilize chave só de Gemini sem habilitar Maps APIs no mesmo projeto.",
        ]
        return base

    remediation = [
        "Abra https://console.cloud.google.com/apis/credentials e edite a chave usada em GOOGLE_MAPS_API_KEY.",
        "Em API restrictions: inclua Geocoding API + Places API (New) OU use 'Don't restrict' em dev.",
        "Habilite billing: https://console.cloud.google.com/billing",
        "Ative APIs: https://console.cloud.google.com/apis/library/geocoding-backend.googleapis.com",
        "Ative APIs: https://console.cloud.google.com/apis/library/places.googleapis.com",
        "Aguarde ~5 min e rode: python tools/maps_health_check.py",
        "Enquanto isso MAPS_FALLBACK_ENABLED=1 usa Nominatim + Overpass (OSM).",
    ]
    base["remediation"] = remediation

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
            err = pr.json().get("error", {}) if pr.headers.get("content-type", "").startswith("application/json") else {}
            base["places_new"] = {
                "ok": False,
                "status": pr.status_code,
                "message": err.get("message") or pr.text[:200],
            }
    except Exception as exc:
        base["places_new"] = {"ok": False, "status": "EXCEPTION", "message": str(exc)}

    base["ok"] = bool(
        base.get("geocoding", {}).get("ok") and base.get("places_new", {}).get("ok")
    )
    return base
