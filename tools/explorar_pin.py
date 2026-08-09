"""Resolve o pin do Explorar para bairro/endereço — não rio, parque ou orla."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.bairro_normalize import fold_texto, normalizar_bairro
from tools.maps_fallback import suggest_nominatim

_FIXTURE_COCO = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "ibge_bairros"
    / "fixtures"
    / "coco_ce.geojson"
)
_SKIP_PARTS = frozenset(
    {"brasil", "brazil", "regiao nordeste", "nordeste", "ce", "ceara"}
)

_DROP_CLASS = frozenset({"waterway", "natural", "leisure", "highway", "tourism", "amenity"})
_KEEP_PLACE_TYPES = frozenset(
    {"suburb", "neighbourhood", "neighborhood", "quarter", "city_district", "town", "city"}
)


def _fold_q(q: str) -> str:
    return normalizar_bairro(q or "")


def filtrar_pins_nominatim(rows: list[dict[str, Any]], q: str) -> list[dict[str, Any]]:
    qn = _fold_q(q)
    keep_park = "parque" in qn or "park" in qn
    keep_river = " rio" in f" {qn}" or qn.startswith("rio ") or "river" in qn
    keep_road = any(t in qn for t in ("rua ", "av ", "avenida", "alameda", "travessa"))
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict) or row.get("lat") is None or row.get("lng") is None:
            continue
        klass = str(row.get("osm_class") or "").lower()
        typ = str(row.get("osm_type_tag") or "").lower()
        if klass == "leisure" and typ == "park" and keep_park:
            out.append(row)
            continue
        if klass == "waterway" and keep_river:
            out.append(row)
            continue
        if klass == "highway" and keep_road:
            out.append(row)
            continue
        if klass in _DROP_CLASS:
            continue
        if klass == "place" and typ and typ not in _KEEP_PLACE_TYPES:
            continue
        out.append(row)
    return out


def anexar_coords_sugestoes(
    places: list[dict[str, Any]],
    osm_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    osm_ok = filtrar_pins_nominatim(osm_rows, " ".join(
        str(p.get("bairro") or "") for p in places
    ) or "bairro")
    by_name: dict[str, dict[str, Any]] = {}
    for row in osm_ok:
        key = normalizar_bairro(str(row.get("bairro") or ""))
        if key and key not in by_name:
            by_name[key] = row
    out: list[dict[str, Any]] = []
    for p in places:
        item = dict(p)
        if item.get("lat") is None or item.get("lng") is None:
            hit = by_name.get(normalizar_bairro(str(item.get("bairro") or "")))
            if hit:
                item["lat"] = hit["lat"]
                item["lng"] = hit["lng"]
        out.append(item)
    return out


def parse_bairro_cidade(q: str) -> tuple[str, str]:
    parts = [p.strip() for p in (q or "").replace(" - ", ",").split(",") if p.strip()]
    bairro = parts[0] if parts else ""
    cidade = ""
    for p in parts[1:]:
        pn = fold_texto(p)
        if pn in _SKIP_PARTS:
            continue
        cidade = p.split("-")[0].strip()
        break
    return bairro, cidade


def parse_lugar_explorar(q: str) -> dict[str, str | None]:
    bairro, cidade = parse_bairro_cidade(q)
    uf: str | None = None
    for p in (q or "").replace(" - ", ",").split(","):
        token = p.strip()
        if len(token) == 2 and token.isalpha():
            uf = token.upper()
            break
    if cidade and not uf:
        try:
            from tools.ibge_tools import buscar_municipio

            hit = buscar_municipio(cidade, "")
            if isinstance(hit, dict) and hit.get("uf"):
                uf = str(hit["uf"]).upper()
        except Exception:
            uf = None
    return {
        "bairro": bairro.strip() or None,
        "cidade": cidade.strip() or None,
        "uf": uf,
    }


def centroide_ibge_bairro(bairro: str, cidade: str) -> dict[str, Any] | None:
    from shapely.geometry import Polygon

    from tools.bairro_poligono import load_fixture_geojson, resolver_bairro_poligono
    from tools.ibge_tools import _MUNICIPIOS_IBGE

    chave = fold_texto(cidade or "")
    mun = _MUNICIPIOS_IBGE.get(chave)
    if not mun or not (bairro or "").strip():
        return None
    id_mun, _nome, uf = mun
    hit = resolver_bairro_poligono(id_municipio=id_mun, bairro=bairro, uf=uf)
    if hit is None and fold_texto(bairro) == "coco" and id_mun == "2304400" and _FIXTURE_COCO.is_file():
        hit = resolver_bairro_poligono(
            id_municipio=id_mun,
            bairro=bairro,
            _store=load_fixture_geojson(_FIXTURE_COCO),
        )
    ring = (hit or {}).get("ring") or []
    if len(ring) < 4:
        return None
    coords = list(ring)
    if coords[0] != coords[-1]:
        coords = coords + [coords[0]]
    poly = Polygon(coords)
    if not poly.is_valid:
        poly = poly.buffer(0)
    c = poly.centroid
    return {"lat": float(c.y), "lng": float(c.x), "fonte": "ibge_bairro_centroide"}


def resolver_explorar_pin(
    q: str,
    *,
    bias_lat: float | None = None,
    bias_lng: float | None = None,
) -> dict[str, Any] | None:
    del bias_lat, bias_lng
    bairro, cidade = parse_bairro_cidade(q)
    ibge = centroide_ibge_bairro(bairro, cidade) if cidade else None
    if ibge:
        return ibge
    rows = suggest_nominatim(q, None, None)
    ok = filtrar_pins_nominatim(list(rows or []), q)
    if not ok:
        return None
    hit = ok[0]
    return {"lat": float(hit["lat"]), "lng": float(hit["lng"]), "fonte": "nominatim_bairro"}
