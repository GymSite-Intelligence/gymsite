"""Isócronas reais 5/10/15 min — ORS se houver chave, senão Valhalla OSM.de."""
from __future__ import annotations

import os
from typing import Any, Literal

import httpx

Modo = Literal["pe", "carro"]

_VALHALLA = os.getenv(
    "VALHALLA_ISOCHRONE_URL",
    "https://valhalla1.openstreetmap.de/isochrone",
).strip()
_ORS_KEY = (os.getenv("ORS_API_KEY") or "").strip()
_ORS_URL = "https://api.openrouteservice.org/v2/isochrones/{profile}"

_VALHALLA_COSTING = {"pe": "pedestrian", "carro": "auto"}
_ORS_PROFILE = {"pe": "foot-walking", "carro": "driving-car"}


def _ring_lonlat_to_latlng(coords: list) -> list[list[float]]:
    ring = coords[0] if coords and isinstance(coords[0][0], (list, tuple)) else coords
    out: list[list[float]] = []
    for p in ring:
        if not isinstance(p, (list, tuple)) or len(p) < 2:
            continue
        out.append([float(p[1]), float(p[0])])
    return out


def _outer_rings(geom: dict[str, Any]) -> list[list[list[float]]]:
    typ = str(geom.get("type") or "").lower()
    coords = geom.get("coordinates") or []
    if typ == "polygon":
        ring = _ring_lonlat_to_latlng(coords)
        return [ring] if len(ring) >= 4 else []
    if typ == "multipolygon":
        out: list[list[list[float]]] = []
        for poly in coords:
            ring = _ring_lonlat_to_latlng(poly)
            if len(ring) >= 4:
                out.append(ring)
        return out
    return []


def parse_isochrone_geojson(data: dict[str, Any]) -> dict[str, list[list[float]]]:
    features = data.get("features") if isinstance(data, dict) else None
    if not isinstance(features, list):
        return {}
    by_min: dict[int, list[list[float]]] = {}
    for feat in features:
        if not isinstance(feat, dict):
            continue
        props = feat.get("properties") or {}
        minutes = props.get("contour")
        if minutes is None and props.get("value") is not None:
            minutes = float(props["value"]) / 60.0
        try:
            m = int(round(float(minutes)))
        except (TypeError, ValueError):
            continue
        rings = _outer_rings(feat.get("geometry") or {})
        if rings:
            by_min[m] = max(rings, key=len)
    out: dict[str, list[list[float]]] = {}
    if 5 in by_min:
        out["m5"] = by_min[5]
    if 10 in by_min:
        out["m10"] = by_min[10]
    if 15 in by_min:
        out["m15"] = by_min[15]
    return out


def _ors(lat: float, lng: float, modo: Modo) -> dict[str, Any]:
    profile = _ORS_PROFILE[modo]
    headers = {"Authorization": _ORS_KEY, "Content-Type": "application/json"}
    body = {
        "locations": [[lng, lat]],
        "range": [300, 600, 900],
        "range_type": "time",
        "attributes": ["area"],
    }
    with httpx.Client(timeout=25, headers={"User-Agent": "GymSiteExplorar/1.0"}) as c:
        r = c.post(_ORS_URL.format(profile=profile), headers=headers, json=body)
    r.raise_for_status()
    rings = parse_isochrone_geojson(r.json())
    if len(rings) < 3:
        raise ValueError("ORS isócrona incompleta")
    return {**rings, "fonte": "ors"}


def _valhalla(lat: float, lng: float, modo: Modo) -> dict[str, Any]:
    costing = _VALHALLA_COSTING[modo]
    body = {
        "locations": [{"lat": lat, "lon": lng}],
        "costing": costing,
        "contours": [{"time": 5}, {"time": 10}, {"time": 15}],
        "polygons": True,
    }
    with httpx.Client(timeout=25, headers={"User-Agent": "GymSiteExplorar/1.0"}) as c:
        r = c.post(_VALHALLA, json=body)
    r.raise_for_status()
    rings = parse_isochrone_geojson(r.json())
    if len(rings) < 3:
        raise ValueError("Valhalla isócrona incompleta")
    return {**rings, "fonte": "valhalla"}


def fetch_isocronas(lat: float, lng: float, modo: Modo = "pe") -> dict[str, Any]:
    if modo not in _VALHALLA_COSTING:
        modo = "pe"
    if _ORS_KEY:
        try:
            return _ors(lat, lng, modo)
        except Exception:
            pass
    return _valhalla(lat, lng, modo)
