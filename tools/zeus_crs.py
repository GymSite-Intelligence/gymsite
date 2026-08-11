"""ZEUS — reprojeção de malhas municipais para WGS84 (lon/lat)."""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Any

logger = logging.getLogger("gymsite.zeus_crs")

_EPSG_RE = re.compile(r"EPSG[:\s]*:?\s*(\d+)", re.I)
_URN_RE = re.compile(r"EPSG::(\d+)", re.I)


def extrair_epsg(crs_hint: Any) -> str | None:
    """Aceita 'EPSG:31983', URN OGC, int ou dict GeoJSON crs."""
    if crs_hint is None:
        return None
    if isinstance(crs_hint, int):
        return f"EPSG:{crs_hint}"
    if isinstance(crs_hint, dict):
        props = crs_hint.get("properties") or {}
        name = props.get("name") or crs_hint.get("name") or ""
        return extrair_epsg(name)
    s = str(crs_hint).strip()
    if not s:
        return None
    if s.upper().startswith("EPSG:"):
        return s.upper().replace(" ", "")
    m = _URN_RE.search(s) or _EPSG_RE.search(s)
    if m:
        return f"EPSG:{m.group(1)}"
    return None


def crs_de_feature_collection(fc: dict, *, default: str | None = None) -> str:
    """CRS do FeatureCollection ou default (WGS84 se omitido)."""
    code = extrair_epsg((fc or {}).get("crs")) or extrair_epsg(default)
    return code or "EPSG:4326"


@lru_cache(maxsize=8)
def _transformer(crs_from: str):
    from pyproj import Transformer

    return Transformer.from_crs(crs_from, "EPSG:4326", always_xy=True)


def para_wgs84(x: float, y: float, crs_from: str) -> tuple[float, float]:
    """(x,y) no CRS origem → (lon, lat) WGS84. EPSG:4326 = no-op."""
    crs = extrair_epsg(crs_from) or "EPSG:4326"
    if crs in ("EPSG:4326", "EPSG:4674"):  # 4674 ≈ lat/lon SIRGAS
        # GeoJSON padrão é lon,lat; se já for graus, devolve.
        if abs(x) <= 180 and abs(y) <= 90:
            return float(x), float(y)
        # Se parecer UTM mas rotulado 4326, não inventa — devolve como veio.
        return float(x), float(y)
    try:
        lon, lat = _transformer(crs).transform(float(x), float(y))
        return float(lon), float(lat)
    except Exception as e:
        logger.warning("zeus CRS falha %s→4326: %s", crs, e)
        return float(x), float(y)


def anel_para_wgs84(
    ring: list[tuple[float, float]], crs_from: str,
) -> list[tuple[float, float]]:
    crs = extrair_epsg(crs_from) or "EPSG:4326"
    if crs in ("EPSG:4326", "EPSG:4674"):
        # Detecta UTM disfarçado (metros): valores grandes.
        if ring and (abs(ring[0][0]) > 180 or abs(ring[0][1]) > 90):
            logger.warning("anel parece UTM mas CRS=%s — não reconverte às cegas", crs)
        return [(float(a), float(b)) for a, b in ring]
    return [para_wgs84(a, b, crs) for a, b in ring]
