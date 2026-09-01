"""VEC-378 Fase 2 — POIs/âncoras via Overpass (paridade OndeAbrir ponto físico).

Categorias: parking, school, university, hospital, bus_station, supermarket.
Fail-soft + cache disco. Não busca academias (concorrência = SearchAPI).
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import time
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger("gymsite.osm_pois")

_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_USER_AGENT = "GymSite-Intelligence/1.0 (+https://getgymsite.com.br; osm_pois VEC-378)"
_CACHE_DIR = Path(__file__).resolve().parent / "cache" / "osm_pois"
_CACHE_TTL_S = 30 * 24 * 3600  # 30 dias

# categoria produto → filtros Overpass (tag=valor ou tag~regex)
_CAT_FILTERS: dict[str, list[tuple[str, str, str]]] = {
    # (element_kind ignored — we emit both node/way), key, match, mode eq|re
    "parking": [("amenity", "parking", "eq")],
    "school": [("amenity", "school", "eq")],
    "university": [("amenity", "university", "eq")],
    "hospital": [("amenity", "hospital|clinic", "re")],
    "bus_station": [
        ("amenity", "bus_station", "eq"),
        ("public_transport", "stop_position|platform|station", "re"),
        ("railway", "station|halt", "re"),
    ],
    "supermarket": [
        ("shop", "supermarket|mall|department_store", "re"),
    ],
}

DEFAULT_CATEGORIAS: tuple[str, ...] = tuple(_CAT_FILTERS.keys())

# tipo_polo para anchoring_tools.calcular_score_ancoragem
_TIPO_POLO: dict[str, str] = {
    "parking": "estacionamento",
    "school": "educacao",
    "university": "educacao",
    "hospital": "saude",
    "bus_station": "terminal_transporte",
    "supermarket": "atacadista",
}


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def _cache_key(lat: float, lng: float, raio: int, cats: Iterable[str]) -> str:
    grid_lat = round(lat, 3)
    grid_lng = round(lng, 3)
    cat_s = ",".join(sorted(cats))
    raw = f"pois|{grid_lat}|{grid_lng}|{raio}|{cat_s}"
    return hashlib.sha256(raw.encode()).hexdigest()[:40]


def _cache_path(key: str) -> Path:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR / f"{key}.json"


def _cache_get(key: str) -> dict[str, Any] | None:
    path = _cache_path(key)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - float(data.get("_cached_at") or 0) > _CACHE_TTL_S:
            return None
        return data.get("payload") if isinstance(data.get("payload"), dict) else None
    except Exception:
        return None


def _cache_put(key: str, payload: dict[str, Any]) -> None:
    try:
        path = _cache_path(key)
        path.write_text(
            json.dumps({"_cached_at": time.time(), "payload": payload}, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as e:
        logger.warning("osm_pois: cache write falhou: %s", e)


def _build_overpass_query(lat: float, lng: float, raio: int, categorias: list[str]) -> str:
    parts: list[str] = []
    for cat in categorias:
        for key, val, mode in _CAT_FILTERS.get(cat, []):
            if mode == "eq":
                filt = f'["{key}"="{val}"]'
            else:
                filt = f'["{key}"~"{val}"]'
            parts.append(f"node(around:{raio},{lat},{lng}){filt};")
            parts.append(f"way(around:{raio},{lat},{lng}){filt};")
    body = "\n      ".join(parts)
    return f"""
    [out:json][timeout:25];
    (
      {body}
    );
    out center 80;
    """


def _classify_element(tags: dict) -> str | None:
    amenity = (tags.get("amenity") or "").lower()
    shop = (tags.get("shop") or "").lower()
    railway = (tags.get("railway") or "").lower()
    pt = (tags.get("public_transport") or "").lower()
    if amenity == "parking":
        return "parking"
    if amenity == "school":
        return "school"
    if amenity == "university":
        return "university"
    if amenity in ("hospital", "clinic"):
        return "hospital"
    if amenity == "bus_station" or pt in ("stop_position", "platform", "station") or railway in ("station", "halt"):
        return "bus_station"
    if shop in ("supermarket", "mall", "department_store"):
        return "supermarket"
    return None


def _element_latlng(el: dict) -> tuple[float, float] | None:
    lat, lon = el.get("lat"), el.get("lon")
    if lat is None or lon is None:
        c = el.get("center") or {}
        lat, lon = c.get("lat"), c.get("lon")
    try:
        if lat is None or lon is None:
            return None
        return float(lat), float(lon)
    except (TypeError, ValueError):
        return None


def osm_pois(
    lat: float,
    lng: float,
    *,
    raio_m: int = 1000,
    categorias: list[str] | None = None,
    max_pois: int = 60,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Busca âncoras OSM no raio. Retorno fail-soft com carimbo P-010."""
    try:
        lat_f, lng_f = float(lat), float(lng)
    except (TypeError, ValueError):
        return {
            "status": "erro",
            "pois": [],
            "contagens": {},
            "fonte": "overpass_osm",
            "carimbo": "osm_pois · coords inválidas",
        }

    raio = max(200, min(int(raio_m), 3000))
    cats = [c for c in (categorias or list(DEFAULT_CATEGORIAS)) if c in _CAT_FILTERS]
    if not cats:
        cats = list(DEFAULT_CATEGORIAS)
    lim = max(1, min(int(max_pois), 80))

    key = _cache_key(lat_f, lng_f, raio, cats)
    if use_cache:
        hit = _cache_get(key)
        if hit is not None:
            hit = dict(hit)
            hit["cache"] = "hit"
            return hit

    query = _build_overpass_query(lat_f, lng_f, raio, cats)
    pois: list[dict[str, Any]] = []
    try:
        import httpx

        with httpx.Client(timeout=30.0, headers={"User-Agent": _USER_AGENT}) as client:
            resp = client.post(_OVERPASS_URL, data={"data": query})
        if resp.status_code != 200:
            logger.warning("osm_pois: HTTP %s", resp.status_code)
            return {
                "status": "indisponivel",
                "pois": [],
                "contagens": {c: 0 for c in cats},
                "fonte": "overpass_osm",
                "carimbo": f"osm_pois · Overpass HTTP {resp.status_code} · raio {raio}m",
                "cache": "miss",
            }
        elements = (resp.json() or {}).get("elements") or []
    except Exception as e:
        logger.warning("osm_pois: falha Overpass: %s", e)
        return {
            "status": "indisponivel",
            "pois": [],
            "contagens": {c: 0 for c in cats},
            "fonte": "overpass_osm",
            "carimbo": f"osm_pois · erro: {type(e).__name__} · raio {raio}m",
            "cache": "miss",
        }

    seen: set[str] = set()
    for el in elements:
        tags = el.get("tags") or {}
        cat = _classify_element(tags)
        if not cat or cat not in cats:
            continue
        coords = _element_latlng(el)
        if not coords:
            continue
        plat, plng = coords
        dist = int(_haversine_m(lat_f, lng_f, plat, plng))
        if dist > raio:
            continue
        nome = tags.get("name") or tags.get("brand") or cat
        dedup = f"{cat}|{nome}|{round(plat, 4)}|{round(plng, 4)}"
        if dedup in seen:
            continue
        seen.add(dedup)
        osm_id = el.get("id", "")
        pois.append({
            "nome": str(nome)[:80],
            "categoria": cat,
            "tipo_polo": _TIPO_POLO.get(cat, cat),
            "lat": plat,
            "lng": plng,
            "distancia_m": dist,
            "place_id": f"osm/{el.get('type', 'node')}/{osm_id}",
            "fonte": "overpass_osm",
        })

    pois.sort(key=lambda p: (p["distancia_m"], p["categoria"]))
    pois = pois[:lim]
    contagens = {c: 0 for c in cats}
    for p in pois:
        contagens[p["categoria"]] = contagens.get(p["categoria"], 0) + 1

    payload = {
        "status": "ok" if pois else "ok_vazio",
        "pois": pois,
        "contagens": contagens,
        "n_pois": len(pois),
        "raio_m": raio,
        "fonte": "overpass_osm",
        "carimbo": (
            f"{len(pois)} POIs · raio {raio}m · Overpass OSM · "
            "© OpenStreetMap contributors"
        ),
        "cache": "miss",
    }
    if use_cache:
        _cache_put(key, {k: v for k, v in payload.items() if k != "cache"})
    return payload


def polos_para_ancoragem(
    lat: float,
    lng: float,
    *,
    raio_m: int = 2000,
) -> list[dict[str, Any]]:
    """Shape compatível com calcular_score_ancoragem (place_id, nome, lat, lng, tipo_polo)."""
    out = osm_pois(lat, lng, raio_m=raio_m)
    polos: list[dict[str, Any]] = []
    for p in out.get("pois") or []:
        if p.get("categoria") == "parking":
            # parking entra no resumo; score de polo foca geradores de fluxo
            continue
        polos.append({
            "place_id": p.get("place_id"),
            "nome": p.get("nome"),
            "lat": p.get("lat"),
            "lng": p.get("lng"),
            "tipo_polo": p.get("tipo_polo"),
            "categoria": p.get("categoria"),
            "distancia_m": p.get("distancia_m"),
            "fonte": "overpass_osm",
        })
    return polos


def resumo_ancoras_ondeabrir(
    lat: float,
    lng: float,
    *,
    raio_m: int = 1000,
) -> dict[str, Any]:
    """Bloco pronto pro relatório: contagens + top âncoras com distância."""
    raw = osm_pois(lat, lng, raio_m=raio_m)
    pois = list(raw.get("pois") or [])
    cont = dict(raw.get("contagens") or {})
    top = [
        {
            "nome": p["nome"],
            "categoria": p["categoria"],
            "distancia_m": p["distancia_m"],
        }
        for p in pois[:12]
    ]
    return {
        "status": raw.get("status"),
        "estacionamentos_n": cont.get("parking", 0),
        "escolas_n": cont.get("school", 0) + cont.get("university", 0),
        "saude_n": cont.get("hospital", 0),
        "transporte_n": cont.get("bus_station", 0),
        "comercio_ancora_n": cont.get("supermarket", 0),
        "ancoras_top": top,
        "fonte": raw.get("fonte"),
        "carimbo": raw.get("carimbo"),
        "raio_m": raw.get("raio_m"),
    }
