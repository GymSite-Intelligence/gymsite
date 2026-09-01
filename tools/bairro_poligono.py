"""IBGE neighborhood polygon helpers (Spec C W1).

Point-in-polygon + fixture load. Resolver (match by name) is Task 2.
Runtime must not hit IBGE FTP per report — only local files / injected store.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict

from shapely.geometry import Point, Polygon


class BairroPoligono(TypedDict, total=False):
    cd_bairro: str | None
    nm_bairro: str
    id_municipio: str
    ring: list[tuple[float, float]]  # (lon, lat)
    fonte: str
    area_km2: float | None


def point_in_ring(lon: float, lat: float, ring: list[tuple[float, float]]) -> bool:
    """True if (lon, lat) is inside the exterior ring (closed or open)."""
    if not ring or len(ring) < 3:
        return False
    coords = list(ring)
    if coords[0] != coords[-1]:
        coords = coords + [coords[0]]
    poly = Polygon(coords)
    if not poly.is_valid:
        poly = poly.buffer(0)
    return bool(poly.contains(Point(lon, lat)) or poly.touches(Point(lon, lat)))


def _ring_from_coords(coords: list) -> list[tuple[float, float]]:
    """GeoJSON polygon exterior → list[(lon, lat)]."""
    exterior = coords[0] if coords and isinstance(coords[0][0], (list, tuple)) else coords
    return [(float(p[0]), float(p[1])) for p in exterior]


def _feature_to_bairro(feat: dict[str, Any]) -> BairroPoligono | None:
    geom = feat.get("geometry") or {}
    props = feat.get("properties") or {}
    if (geom.get("type") or "").lower() != "polygon":
        return None
    ring = _ring_from_coords(geom.get("coordinates") or [])
    if len(ring) < 4:
        return None
    id_mun = str(props.get("CD_MUN") or props.get("id_municipio") or "").strip()
    nm = str(props.get("NM_BAIRRO") or props.get("nm_bairro") or "").strip()
    if not id_mun or not nm:
        return None
    cd = props.get("CD_BAIRRO") or props.get("cd_bairro")
    area_km2: float | None = None
    try:
        poly = Polygon(ring if ring[0] == ring[-1] else ring + [ring[0]])
        if poly.is_valid:
            # deg² → rough km² at equator scale (good enough for stamp)
            area_km2 = round(poly.area * (111.0 ** 2), 3)
    except Exception:
        area_km2 = None
    return BairroPoligono(
        cd_bairro=str(cd) if cd is not None else None,
        nm_bairro=nm,
        id_municipio=id_mun,
        ring=ring,
        fonte="ibge_bairro",
        area_km2=area_km2,
    )


def load_fixture_geojson(path: str | Path) -> list[BairroPoligono]:
    """Load FeatureCollection of Polygon bairros from a local GeoJSON file."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    feats = raw.get("features") if isinstance(raw, dict) else None
    if not isinstance(feats, list):
        return []
    out: list[BairroPoligono] = []
    for f in feats:
        if not isinstance(f, dict):
            continue
        bp = _feature_to_bairro(f)
        if bp:
            out.append(bp)
    return out


_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "ibge_bairros"


def _load_uf_gpkg(uf: str) -> list[BairroPoligono]:
    """Load local `{UF}.gpkg` if present. No network. Empty list if missing/unreadable."""
    path = _DATA_DIR / f"{(uf or '').strip().upper()}.gpkg"
    if not path.is_file():
        return []
    try:
        import geopandas as gpd

        gdf = gpd.read_file(path)
    except Exception:
        return []
    out: list[BairroPoligono] = []
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        if geom.geom_type == "MultiPolygon":
            geom = list(geom.geoms)[0]
        if geom.geom_type != "Polygon":
            continue
        ring = [(float(x), float(y)) for x, y in geom.exterior.coords]

        def _col(name: str):
            return row[name] if name in row.index else None

        bp = _feature_to_bairro({
            "type": "Feature",
            "properties": {
                "CD_BAIRRO": _col("CD_BAIRRO"),
                "NM_BAIRRO": _col("NM_BAIRRO"),
                "CD_MUN": _col("CD_MUN"),
            },
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        })
        if bp:
            out.append(bp)
    return out


def resolver_bairro_poligono(
    *,
    id_municipio: str | None,
    bairro: str,
    cidade: str | None = None,
    uf: str | None = None,
    _store: list[BairroPoligono] | None = None,
) -> BairroPoligono | None:
    """Match bairro polygon by id_municipio + folded name. No invent on miss.

    `_store` injects fixtures/tests. Else tries `data/ibge_bairros/{UF}.gpkg` when `uf` set.
    """
    from tools.bairro_normalize import normalizar_bairro, resolver_bairro_canonico

    alvo = normalizar_bairro(bairro or "")
    idm = (id_municipio or "").strip()
    if not alvo or not idm:
        return None
    store = _store if _store is not None else (_load_uf_gpkg(uf) if uf else [])

    def _match(nome_fold: str) -> BairroPoligono | None:
        for bp in store:
            if (bp.get("id_municipio") or "").strip() != idm:
                continue
            if normalizar_bairro(bp.get("nm_bairro") or "") == nome_fold:
                return bp
        return None

    hit = _match(alvo)
    if hit:
        return hit
    canon = resolver_bairro_canonico(bairro or "", uf=uf or "", cidade=cidade or "")
    canon_fold = normalizar_bairro(canon)
    if canon_fold and canon_fold != alvo:
        return _match(canon_fold)
    return None
