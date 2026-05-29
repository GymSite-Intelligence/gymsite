"""
Fallbacks gratuitos quando Google Maps Platform retorna REQUEST_DENIED / bloqueio de API key.

- Geocoding: OpenStreetMap Nominatim (uso com User-Agent identificado)
- Academias no raio: Overpass API (OSM leisure=fitness_centre, amenity=gym)
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_USER_AGENT = os.getenv(
    "MAPS_FALLBACK_USER_AGENT",
    "GymSite-Intelligence/1.0 (prospeccao academias; contacto vectracargo.com.br)",
)


def fallback_habilitado() -> bool:
    return os.getenv("MAPS_FALLBACK_ENABLED", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def geocode_nominatim(endereco: str) -> dict:
    """Geocode via Nominatim (BR)."""
    if not endereco.strip():
        return {"error": "endereco vazio"}
    try:
        with httpx.Client(timeout=15, headers={"User-Agent": _USER_AGENT}) as c:
            r = c.get(
                _NOMINATIM_URL,
                params={
                    "q": endereco,
                    "format": "json",
                    "limit": 1,
                    "countrycodes": "br",
                    "addressdetails": 1,
                },
            )
        if r.status_code != 200:
            return {"error": f"Nominatim HTTP {r.status_code}"}
        rows = r.json()
        if not rows:
            return {"error": "Nominatim: endereço não encontrado"}
        item = rows[0]
        return {
            "lat": float(item["lat"]),
            "lng": float(item["lon"]),
            "formatted_address": item.get("display_name", endereco),
            "place_id": f"osm_{item.get('osm_type','')}_{item.get('osm_id','')}",
            "fonte_geocode": "nominatim",
        }
    except Exception as exc:
        return {"error": f"Nominatim falhou: {exc}"}


def _overpass_element_to_place(el: dict, lat_center: float, lng_center: float) -> dict:
    tags = el.get("tags") or {}
    nome = tags.get("name") or tags.get("brand") or "Academia (OSM)"
    lat = el.get("lat")
    lng = el.get("lon")
    if lat is None or lng is None:
        center = el.get("center") or {}
        lat = center.get("lat")
        lng = center.get("lon")
    lat_f = float(lat or 0)
    lng_f = float(lng or 0)
    endereco_parts = [
        tags.get("addr:street"),
        tags.get("addr:housenumber"),
        tags.get("addr:suburb") or tags.get("addr:neighbourhood"),
        tags.get("addr:city"),
    ]
    endereco = ", ".join(p for p in endereco_parts if p) or tags.get("addr:full", "")
    osm_id = el.get("id", "")
    return {
        "place_id": f"osm/{el.get('type','node')}/{osm_id}",
        "nome": nome,
        "endereco": endereco,
        "lat": lat_f,
        "lng": lng_f,
        "tipos": ["gym", "fitness_center"],
        "status": "OPERATIONAL",
        "rating": None,
        "num_avaliacoes": 0,
        "telefone": tags.get("phone") or tags.get("contact:phone") or "",
        "website": tags.get("website") or tags.get("contact:website") or "",
        "tem_24h": False,
        "horarios": [],
        "fonte": "overpass_osm",
    }


def overpass_fitness_near(
    latitude: float,
    longitude: float,
    raio_metros: int = 3000,
    *,
    limit: int = 20,
) -> dict[str, Any]:
    """
    Busca academias / fitness no raio via Overpass (OSM).
    Retorna {"places": [...], "fonte": "overpass"} ou {"erro": ...}.
    """
    raio = max(200, min(int(raio_metros), 15000))
    lim = max(1, min(int(limit), 40))
    query = f"""
    [out:json][timeout:25];
    (
      node(around:{raio},{latitude},{longitude})["leisure"="fitness_centre"];
      way(around:{raio},{latitude},{longitude})["leisure"="fitness_centre"];
      node(around:{raio},{latitude},{longitude})["amenity"="gym"];
      way(around:{raio},{latitude},{longitude})["amenity"="gym"];
    );
    out center {lim};
    """
    try:
        with httpx.Client(timeout=30, headers={"User-Agent": _USER_AGENT}) as c:
            r = c.post(_OVERPASS_URL, data={"data": query})
        if r.status_code != 200:
            return {"erro": f"Overpass HTTP {r.status_code}", "places": []}
        data = r.json()
        elements = data.get("elements") or []
        places = [
            _overpass_element_to_place(el, latitude, longitude) for el in elements
        ]
        # dedupe por nome+coord aproximada
        seen: set[str] = set()
        uniq: list[dict] = []
        for p in places:
            key = f"{p.get('nome','')}|{round(p.get('lat',0),4)}|{round(p.get('lng',0),4)}"
            if key in seen:
                continue
            seen.add(key)
            uniq.append(p)
        return {"places": uniq[:lim], "fonte": "overpass_osm", "total": len(uniq)}
    except Exception as exc:
        return {"erro": f"Overpass falhou: {exc}", "places": []}


def overpass_fitness_to_concorrentes(
    places: list[dict],
    lat_centro: float,
    lng_centro: float,
) -> list[dict]:
    """Converte places do fallback para formato competitor_tools."""
    from tools.maps_tools import calcular_distancia_km

    out = []
    for p in places:
        plat, plng = p.get("lat", 0), p.get("lng", 0)
        out.append(
            {
                "place_id": p.get("place_id", ""),
                "nome": p.get("nome", ""),
                "endereco": p.get("endereco", ""),
                "lat": plat,
                "lng": plng,
                "distancia_km": round(calcular_distancia_km(lat_centro, lng_centro, plat, plng), 2),
                "rating": p.get("rating"),
                "num_avaliacoes": p.get("num_avaliacoes", 0),
                "nivel_preco": "",
                "status": p.get("status", ""),
                "tipos": p.get("tipos", []),
                "telefone": p.get("telefone", ""),
                "website": p.get("website", ""),
                "tem_24h": p.get("tem_24h", False),
                "horarios": p.get("horarios", []),
                "fonte_busca": "overpass_osm",
            }
        )
    out.sort(key=lambda x: x["distancia_km"])
    return out
