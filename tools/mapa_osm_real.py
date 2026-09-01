"""Mapas OSM raster para o PDF — tiles + overlay sobre geometria real.

Preferência: segments do motor (fluxo). Fallback mapa: centerline OSM por nome.
Fail-soft: erro → None (SVG permanece).
"""
from __future__ import annotations

import base64
import io
import json
import logging
import math
from pathlib import Path
from typing import Any

logger = logging.getLogger("gymsite.mapa_osm")

_TILE_CACHE_DIR = Path(__file__).resolve().parent.parent / "cache" / "osm_tiles"
_CENTERLINE_CACHE_DIR = Path(__file__).resolve().parent.parent / "cache" / "osm_centerlines"
_TILE_SIZE = 256
_MAX_ZOOM = 17
_MIN_ZOOM = 12
_TILE_URLS = (
    "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
    "https://b.tile.openstreetmap.org/{z}/{x}/{y}.png",
    "https://c.tile.openstreetmap.org/{z}/{x}/{y}.png",
)
_USER_AGENT = "GymSite-Intelligence/1.0 (+https://getgymsite.com.br; maps for PDF reports)"
_CARIMBO = "mapa_osm · tiles OSM · render local · © OpenStreetMap contributors"

_CORES_FLUXO = (
    (0.0, "#94A3B8"),
    (0.40, "#0E5C66"),
    (0.60, "#EA580C"),
    (0.85, "#DC2626"),
    (1.0, "#991B1B"),
)

_COR_ZONA_SIGLA = {
    "ZEDUS": "#16A34A",
    "ZOC": "#16A34A",
    "ZEU": "#16A34A",
    "ZEIS": "#DC2626",
    "ZEA": "#DC2626",
    "ZEPH": "#D97706",
    "ZEPO": "#D97706",
    "ZEI": "#D97706",
    "AEA": "#D97706",
}


def latlon_to_world_px(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    """Web Mercator → pixel mundial (origem NW, zoom OSM)."""
    scale = float(_TILE_SIZE * (2**zoom))
    x = (lon + 180.0) / 360.0 * scale
    siny = math.sin(math.radians(lat))
    siny = min(max(siny, -0.9999), 0.9999)
    y = (0.5 - math.log((1.0 + siny) / (1.0 - siny)) / (4.0 * math.pi)) * scale
    return x, y


def calcular_zoom_otimo(
    bounds: tuple[float, float, float, float],
    width: int = 560,
    height: int = 300,
    *,
    pad_frac: float = 0.12,
) -> int:
    """bounds = (min_lat, min_lon, max_lat, max_lon)."""
    min_lat, min_lon, max_lat, max_lon = bounds
    for zoom in range(_MAX_ZOOM, _MIN_ZOOM - 1, -1):
        x1, y1 = latlon_to_world_px(min_lat, min_lon, zoom)
        x2, y2 = latlon_to_world_px(max_lat, max_lon, zoom)
        bw = abs(x2 - x1) * (1.0 + pad_frac)
        bh = abs(y2 - y1) * (1.0 + pad_frac)
        if bw <= width and bh <= height:
            return zoom
    return _MIN_ZOOM


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _interpolar_hex(c1: str, c2: str, t: float) -> str:
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def cor_fluxo(score_100: float | int | None) -> str:
    try:
        t = max(0.0, min(1.0, float(score_100 or 0) / 100.0))
    except (TypeError, ValueError):
        t = 0.0
    for i in range(len(_CORES_FLUXO) - 1):
        v1, c1 = _CORES_FLUXO[i]
        v2, c2 = _CORES_FLUXO[i + 1]
        if v1 <= t <= v2:
            frac = (t - v1) / (v2 - v1) if v2 != v1 else 0.0
            return _interpolar_hex(c1, c2, frac)
    return _CORES_FLUXO[-1][1]


def cor_zona_sigla(sigla: str | None) -> str:
    s = (sigla or "").upper()
    for k, v in _COR_ZONA_SIGLA.items():
        if s.startswith(k):
            return v
    return "#64748B"


def png_to_data_uri(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def _tile_cache_path(z: int, x: int, y: int) -> Path:
    _TILE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _TILE_CACHE_DIR / f"{z}_{x}_{y}.png"


def _buscar_tile(z: int, x: int, y: int) -> bytes | None:
    n = 2**z
    if x < 0 or y < 0 or x >= n or y >= n:
        return None
    cache_path = _tile_cache_path(z, x, y)
    if cache_path.exists():
        try:
            return cache_path.read_bytes()
        except OSError:
            pass
    try:
        import httpx

        url = _TILE_URLS[(x + y) % len(_TILE_URLS)].format(z=z, x=x, y=y)
        with httpx.Client(timeout=12.0, headers={"User-Agent": _USER_AGENT}) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.content
        try:
            cache_path.write_bytes(data)
        except OSError:
            pass
        return data
    except Exception as e:
        logger.warning("mapa_osm: tile z=%s x=%s y=%s falhou: %s", z, x, y, e)
        return None


def _render_base_tiles(
    center_lat: float,
    center_lng: float,
    zoom: int,
    width: int,
    height: int,
) -> Any | None:
    try:
        from PIL import Image
    except ImportError:
        logger.error("mapa_osm: Pillow indisponível")
        return None

    cx, cy = latlon_to_world_px(center_lat, center_lng, zoom)
    left = cx - width / 2.0
    top = cy - height / 2.0
    x0 = int(math.floor(left / _TILE_SIZE))
    y0 = int(math.floor(top / _TILE_SIZE))
    x1 = int(math.floor((left + width - 1) / _TILE_SIZE))
    y1 = int(math.floor((top + height - 1) / _TILE_SIZE))

    img = Image.new("RGB", (width, height), (241, 245, 249))
    for tx in range(x0, x1 + 1):
        for ty in range(y0, y1 + 1):
            raw = _buscar_tile(zoom, tx, ty)
            if not raw:
                continue
            try:
                tile = Image.open(io.BytesIO(raw)).convert("RGB")
            except Exception:
                continue
            paste_x = int(round(tx * _TILE_SIZE - left))
            paste_y = int(round(ty * _TILE_SIZE - top))
            img.paste(tile, (paste_x, paste_y))
    return img


def _viewport_project(
    lat: float,
    lon: float,
    *,
    center_lat: float,
    center_lng: float,
    zoom: int,
    width: int,
    height: int,
) -> tuple[float, float]:
    wx, wy = latlon_to_world_px(lat, lon, zoom)
    cx, cy = latlon_to_world_px(center_lat, center_lng, zoom)
    return wx - cx + width / 2.0, wy - cy + height / 2.0


def _parse_lonlat(pt: Any) -> tuple[float, float] | None:
    """Aceita [lon, lat] (padrão do projeto) → (lat, lon)."""
    if not isinstance(pt, (list, tuple)) or len(pt) < 2:
        return None
    try:
        a, b = float(pt[0]), float(pt[1])
    except (TypeError, ValueError):
        return None
    if abs(a) >= abs(b):
        return b, a
    return a, b


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def _split_saltos(
    pts: list[tuple[float, float]],
    *,
    max_salto_m: float = 380.0,
) -> list[list[tuple[float, float]]]:
    if len(pts) < 2:
        return []
    segs: list[list[tuple[float, float]]] = [[pts[0]]]
    for p in pts[1:]:
        prev = segs[-1][-1]
        if _haversine_m(prev[0], prev[1], p[0], p[1]) > max_salto_m:
            if len(segs[-1]) >= 2:
                segs.append([p])
            else:
                segs[-1] = [p]
        else:
            segs[-1].append(p)
    return [s for s in segs if len(s) >= 2]


def _clip_perto(
    pts: list[tuple[float, float]],
    center: tuple[float, float],
    *,
    max_m: float = 900.0,
) -> list[tuple[float, float]]:
    clat, clon = center
    return [p for p in pts if _haversine_m(clat, clon, p[0], p[1]) <= max_m]


def _segments_da_via(via: dict, center: tuple[float, float]) -> list[list[tuple[float, float]]]:
    out: list[list[tuple[float, float]]] = []
    raw_segs = via.get("segments")
    if isinstance(raw_segs, list) and raw_segs:
        for seg in raw_segs:
            if not isinstance(seg, (list, tuple)):
                continue
            pts: list[tuple[float, float]] = []
            for pt in seg:
                parsed = _parse_lonlat(pt)
                if parsed:
                    pts.append(parsed)
            pts = _clip_perto(pts, center)
            out.extend(_split_saltos(pts))
        return out

    coords_raw = via.get("coords") or []
    pts = []
    for pt in coords_raw:
        parsed = _parse_lonlat(pt)
        if parsed:
            pts.append(parsed)
    pts = _clip_perto(pts, center)
    return _split_saltos(pts)


def _nome_via_curto(nome: str) -> str:
    n = (nome or "").strip()
    for pref in ("Avenida ", "Av. ", "Av ", "Rua ", "R. ", "Travessa ", "Alameda "):
        if n.lower().startswith(pref.lower()):
            n = n[len(pref):]
            break
    return n[:28]


def _nome_busca_osm(nome: str) -> str:
    n = _nome_via_curto(nome).strip()
    for ch in r"\.^$*+?{}[]|()":
        n = n.replace(ch, "\\" + ch)
    return n


def buscar_centerline_osm(
    nome_via: str,
    centroide: tuple[float, float],
    *,
    raio_m: int = 1200,
) -> list[list[tuple[float, float]]]:
    """Segments (lat,lon) da via no OSM por nome. Cache em disco. Fail-soft → []."""
    lat, lon = float(centroide[0]), float(centroide[1])
    needle = _nome_busca_osm(nome_via)
    if len(needle) < 3:
        return []
    key = f"{needle.lower()}_{lat:.4f}_{lon:.4f}_{raio_m}"
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)[:120]
    cache_path = _CENTERLINE_CACHE_DIR / f"{safe}.json"
    try:
        _CENTERLINE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        if cache_path.exists():
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            segs = data.get("segments") or []
            return [[(float(a), float(b)) for a, b in seg] for seg in segs if len(seg) >= 2]
    except Exception:
        pass

    query = f"""
    [out:json][timeout:25];
    way["highway"]["name"~"{needle}",i](around:{raio_m},{lat},{lon});
    out geom;
    """
    segs_out: list[list[tuple[float, float]]] = []
    try:
        import httpx

        with httpx.Client(timeout=30.0, headers={"User-Agent": _USER_AGENT}) as client:
            resp = client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
            )
            resp.raise_for_status()
            elements = (resp.json() or {}).get("elements") or []
        for el in elements:
            if el.get("type") != "way":
                continue
            geom = el.get("geometry") or []
            pts = [
                (float(p["lat"]), float(p["lon"]))
                for p in geom
                if "lat" in p and "lon" in p
            ]
            pts = _clip_perto(pts, (lat, lon), max_m=float(raio_m))
            segs_out.extend(_split_saltos(pts))
        segs_out.sort(key=len, reverse=True)
        segs_out = segs_out[:8]
        try:
            cache_path.write_text(
                json.dumps({"segments": segs_out}, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass
    except Exception as e:
        logger.warning("mapa_osm: centerline '%s' falhou: %s", nome_via, e)
        return []
    return segs_out


def enriquecer_coords_vias(
    top_vias: list[dict],
    centroide: tuple[float, float],
) -> list[dict]:
    """Motor primeiro; senão centerline OSM por nome (só para desenhar o mapa)."""
    out: list[dict] = []
    for via in top_vias or []:
        if not isinstance(via, dict):
            continue
        v = dict(via)
        segs = _segments_da_via(v, centroide)
        if not segs:
            segs = buscar_centerline_osm(str(v.get("nome_via") or ""), centroide)
            if segs:
                v["segments"] = [[[lon, lat] for lat, lon in seg] for seg in segs]
                flat = [pt for seg in v["segments"] for pt in seg]
                v["coords"] = flat[:80]
                v["fonte_geo"] = "osm_centerline_nome"
        out.append(v)
    return out


def gerar_mapa_top_vias(
    top_vias: list[dict],
    centroide: tuple[float, float],
    *,
    width: int = 560,
    height: int = 300,
    raio_enquadramento_m: float = 550.0,
) -> bytes | None:
    """Overlay das vias sobre tiles OSM — enquadra o entorno do ponto (~550 m)."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.error("mapa_osm: Pillow indisponível")
        return None

    center_lat, center_lng = float(centroide[0]), float(centroide[1])
    vias_ok: list[tuple[str, list[list[tuple[float, float]]], float]] = []

    for via in top_vias or []:
        if not isinstance(via, dict):
            continue
        # Clip mais apertado que o da centerline — só o que cabe no mapa
        segs_raw = _segments_da_via(via, (center_lat, center_lng))
        segs: list[list[tuple[float, float]]] = []
        for seg in segs_raw:
            clipped = _clip_perto(seg, (center_lat, center_lng), max_m=raio_enquadramento_m)
            segs.extend(_split_saltos(clipped))
        if not segs:
            continue
        try:
            fluxo_score = via.get("fluxo_score")
            if fluxo_score is not None:
                score = float(fluxo_score)
            else:
                fluxo_norm = via.get("fluxo_norm")
                score = float(fluxo_norm or 0) * 100
        except (TypeError, ValueError):
            score = 0.0
        vias_ok.append((str(via.get("nome_via") or ""), segs, score))

    if not vias_ok:
        return None

    # Enquadramento fixo no raio do ponto (não deixa avenida longa “afastar” o zoom)
    # ~1° lat ≈ 111 km → delta
    dlat = raio_enquadramento_m / 111_000.0
    dlon = raio_enquadramento_m / (111_000.0 * max(0.2, math.cos(math.radians(center_lat))))
    bounds = (
        center_lat - dlat,
        center_lng - dlon,
        center_lat + dlat,
        center_lng + dlon,
    )
    zoom = calcular_zoom_otimo(bounds, width, height, pad_frac=0.04)
    # Bairro legível: ruas alinhadas ao grid do tile
    zoom = max(zoom, 16)
    zoom = min(zoom, _MAX_ZOOM)

    scale = 2
    W, H = width * scale, height * scale
    img = _render_base_tiles(center_lat, center_lng, zoom, W, H)
    if img is None:
        return None

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    def _px(lat: float, lon: float) -> tuple[float, float]:
        return _viewport_project(
            lat, lon,
            center_lat=center_lat,
            center_lng=center_lng,
            zoom=zoom,
            width=W,
            height=H,
        )

    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    for nome, segs, score in sorted(vias_ok, key=lambda x: x[2]):
        cor = cor_fluxo(score)
        rgb = _hex_to_rgb(cor)
        # Traço fino o bastante para caber na rua do tile
        sw = 7 if score >= 85 else (5 if score >= 60 else 4)
        label_pt: tuple[float, float] | None = None
        best_len = 0
        for seg in segs:
            pixels = [_px(lat, lon) for lat, lon in seg]
            # Descarta pontos fora do canvas (margem)
            pixels = [
                (x, y) for x, y in pixels
                if -20 <= x <= W + 20 and -20 <= y <= H + 20
            ]
            if len(pixels) < 2:
                continue
            xy = [(round(x), round(y)) for x, y in pixels]
            draw.line(xy, fill=(255, 255, 255, 200), width=sw + 3, joint="curve")
            draw.line(xy, fill=rgb + (230,), width=sw, joint="curve")
            if len(xy) > best_len:
                best_len = len(xy)
                mid = xy[len(xy) // 2]
                label_pt = (float(mid[0]), float(mid[1]))

        if label_pt and nome:
            label = _nome_via_curto(nome)
            tx = min(max(label_pt[0] + 4 * scale, 4), W - 80 * scale)
            ty = min(max(label_pt[1] - 10 * scale, 4), H - 40 * scale)
            draw.text((tx + 1, ty + 1), label, fill=(255, 255, 255, 230), font=font)
            draw.text((tx, ty), label, fill=(15, 23, 42, 255), font=font)

    cx, cy = _px(center_lat, center_lng)
    r = 8
    draw.ellipse([cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2], fill=(255, 255, 255, 255))
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(15, 23, 42, 255))

    pad = 8 * scale
    draw.rectangle([pad, H - 28 * scale, W - pad, H - pad], fill=(255, 255, 255, 210))
    draw.text(
        (pad + 6, H - 24 * scale),
        "Vermelho = maior fluxo · ponto = centróide · © OpenStreetMap",
        fill=(71, 85, 105, 255),
        font=font,
    )

    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    img = img.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def gerar_mapa_zoneamento(
    zonas: list[dict],
    ponto: tuple[float, float],
    *,
    width: int = 560,
    height: int = 300,
    raio_graus: float = 0.025,
) -> bytes | None:
    """Overlay de polígonos de zona (lon,lat) já carregados pelo ZEUS."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.error("mapa_osm: Pillow indisponível")
        return None

    lat0, lon0 = float(ponto[0]), float(ponto[1])
    prox: list[dict] = []
    all_lat = [lat0]
    all_lon = [lon0]

    for z in zonas or []:
        if not isinstance(z, dict):
            continue
        poly = z.get("polygon")
        if not poly or len(poly) < 3:
            continue
        pts: list[tuple[float, float]] = []
        for pt in poly:
            if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                continue
            try:
                lo, la = float(pt[0]), float(pt[1])
            except (TypeError, ValueError):
                continue
            pts.append((lo, la))
        if len(pts) < 3:
            continue
        if not any(abs(lo - lon0) <= raio_graus and abs(la - lat0) <= raio_graus for lo, la in pts):
            continue
        prox.append({**z, "polygon": pts})
        for lo, la in pts:
            all_lat.append(la)
            all_lon.append(lo)

    if not prox:
        return None

    bounds = (min(all_lat), min(all_lon), max(all_lat), max(all_lon))
    zoom = calcular_zoom_otimo(bounds, width, height)
    img = _render_base_tiles(lat0, lon0, zoom, width, height)
    if img is None:
        return None

    draw = ImageDraw.Draw(img, "RGBA")
    for z in prox[:40]:
        poly = z["polygon"]
        step = max(1, len(poly) // 50)
        poly = poly[::step]
        pixels = [
            _viewport_project(
                la, lo,
                center_lat=lat0,
                center_lng=lon0,
                zoom=zoom,
                width=width,
                height=height,
            )
            for lo, la in poly
        ]
        if len(pixels) < 3:
            continue
        cor = cor_zona_sigla(z.get("sigla_zona") or z.get("tipo_zona") or z.get("folder"))
        rgb = _hex_to_rgb(cor)
        draw.polygon(
            [(round(x), round(y)) for x, y in pixels],
            fill=rgb + (56,),
            outline=rgb + (200,),
        )

    cx, cy = _viewport_project(
        lat0, lon0,
        center_lat=lat0,
        center_lng=lon0,
        zoom=zoom,
        width=width,
        height=height,
    )
    r = 5
    draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        fill=(15, 23, 42, 255),
        outline=(255, 255, 255, 255),
        width=2,
    )

    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    draw.rectangle([6, height - 22, width - 6, height - 6], fill=(255, 255, 255, 200))
    draw.text(
        (10, height - 20),
        "Zonas especiais · ponto = candidato · © OSM",
        fill=(100, 116, 139, 255),
        font=font,
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def enriquecer_e_render_vias(
    top_vias: list[dict],
    lat: float,
    lng: float,
) -> str | None:
    """Enriquece centerlines se preciso e devolve data URI PNG (fail-soft)."""
    try:
        vias = enriquecer_coords_vias(top_vias, (lat, lng))
        by_nome = {str(v.get("nome_via")): v for v in vias if isinstance(v, dict)}
        for orig in top_vias or []:
            if not isinstance(orig, dict):
                continue
            enriched = by_nome.get(str(orig.get("nome_via")))
            if not enriched:
                continue
            if not orig.get("segments") and enriched.get("segments"):
                orig["segments"] = enriched["segments"]
            if not orig.get("coords") and enriched.get("coords"):
                orig["coords"] = enriched["coords"]
        png = gerar_mapa_top_vias(vias, (lat, lng))
        if png:
            return png_to_data_uri(png)
    except Exception:
        logger.warning("mapa_osm: enriquecer+render vias falhou", exc_info=True)
    return None


def try_mapa_vias_data_uri(
    top_vias: list[dict],
    lat: float,
    lng: float,
) -> str | None:
    """Fail-soft: PNG data URI só com coords já presentes (sem Overpass)."""
    try:
        png = gerar_mapa_top_vias(top_vias, (lat, lng))
        if png:
            return png_to_data_uri(png)
    except Exception:
        logger.warning("mapa_osm: vias PNG falhou", exc_info=True)
    return None


def try_mapa_zonas_data_uri(
    polygons: list[dict],
    lat: float,
    lon: float,
) -> str | None:
    """Fail-soft: PNG data URI ou None."""
    try:
        png = gerar_mapa_zoneamento(polygons, (lat, lon))
        if png:
            return png_to_data_uri(png)
    except Exception:
        logger.warning("mapa_osm: zonas PNG falhou", exc_info=True)
    return None


def carimbo_mapa_osm() -> str:
    return _CARIMBO
