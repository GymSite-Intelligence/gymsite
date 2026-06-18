"""Geocoding gratuito via OpenStreetMap Nominatim — elo que faltava na cascata de
busca de imóveis (SearchAPI/Apify não retornam lat/lon; sem coordenada o zoneamento
point-in-polygon não roda). Sem API key, sem custo. Rate limit obrigatório (ToS): 1 req/s.

Config (intervalo, base_url, user-agent) é DADO recalibrável — vem de param()/env, não
hardcode inline.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx

logger = logging.getLogger("gymsite.nominatim")

_NOMINATIM_URL = (os.getenv("NOMINATIM_URL") or "https://nominatim.openstreetmap.org/search").strip()
_UA = (os.getenv("NOMINATIM_USER_AGENT")
       or "GymSite-Intelligence/1.0 (contato@vectracargo.com.br)")
_last_call = 0.0


def _intervalo_min() -> float:
    """Intervalo mínimo entre chamadas (ToS Nominatim = 1 req/s). Recalibrável via param."""
    try:
        from tools.parametros_metodologia import param

        return float(param("nominatim_intervalo_seg"))
    except Exception:
        return 1.1


def nominatim_geocode(query: str, *, country_code: str = "br", limit: int = 1) -> dict[str, Any] | None:
    """Endereço (completo OU parcial: 'Cocó, Fortaleza, CE') → {lat, lon, display_name,
    address, ...}. None se falhar. Rate-limited (bloqueante, ~1s). Best-effort."""
    global _last_call
    q = (query or "").strip()
    if not q:
        return None
    elapsed = time.time() - _last_call
    intervalo = _intervalo_min()
    if elapsed < intervalo:
        time.sleep(intervalo - elapsed)
    params = {
        "q": q, "format": "json", "limit": max(1, int(limit)),
        "countrycodes": country_code, "addressdetails": 1, "accept-language": "pt-BR",
    }
    try:
        with httpx.Client(timeout=15) as c:
            resp = c.get(_NOMINATIM_URL, params=params, headers={"User-Agent": _UA})
        _last_call = time.time()
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            return None
        top = rows[0]
        return {
            "lat": float(top["lat"]), "lon": float(top["lon"]),
            "display_name": top.get("display_name", ""),
            "type": top.get("type"), "importance": top.get("importance"),
            "address": top.get("address", {}),
            "fonte": "nominatim_osm",
        }
    except Exception as e:
        logger.warning("nominatim falha '%s': %s", q, e)
        _last_call = time.time()
        return None
