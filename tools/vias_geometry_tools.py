"""Geometria das top vias + SVG para PDF (prospecção por fluxo).

Reusa o GeoJSON já calculado pelo motor angular (`run_flow_analysis`) —
não dispara osmnx de novo. Fail-soft: sem coords → sem mapa.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _coords_from_geometry(geom: dict | None) -> list[tuple[float, float]]:
    """Extrai (lon, lat) de LineString / MultiLineString GeoJSON."""
    if not isinstance(geom, dict):
        return []
    t = str(geom.get("type") or "")
    raw = geom.get("coordinates") or []
    out: list[tuple[float, float]] = []
    try:
        if t == "LineString":
            for pt in raw:
                if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    out.append((float(pt[0]), float(pt[1])))
        elif t == "MultiLineString":
            for line in raw:
                if not isinstance(line, (list, tuple)):
                    continue
                for pt in line:
                    if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                        out.append((float(pt[0]), float(pt[1])))
    except (TypeError, ValueError):
        return []
    return out


def _downsample(coords: list[tuple[float, float]], max_pts: int) -> list[tuple[float, float]]:
    if len(coords) <= max_pts or max_pts < 2:
        return coords
    step = max(1, len(coords) // max_pts)
    slim = coords[::step]
    if slim[-1] != coords[-1]:
        slim.append(coords[-1])
    return slim[: max_pts + 1]


def _cor_fluxo(score_100: float | int | None) -> str:
    try:
        t = max(0.0, min(1.0, float(score_100 or 0) / 100.0))
    except (TypeError, ValueError):
        t = 0.0
    if t >= 0.85:
        return "#DC2626"
    if t >= 0.60:
        return "#EA580C"
    if t >= 0.40:
        return "#0E5C66"
    return "#94A3B8"


def expor_geometria_vias(
    features: list[dict] | None,
    top_vias: list[dict] | None,
    *,
    max_pts_per_via: int = 80,
) -> dict[str, Any]:
    """Extrai linestring simplificada por via top (lon,lat).

    Entrada: features do GeoJSON do motor + lista `top_vias` (nome_via, fluxo_score).
    """
    try:
        from tools.fluxo_pedestre_tools import _normalize_street_name
    except Exception:
        def _normalize_street_name(raw):  # type: ignore
            return str(raw or "").strip()

    top = [v for v in (top_vias or []) if isinstance(v, dict) and v.get("nome_via")]
    if not top:
        return {"status": "indisponivel", "motivo": "sem top_vias", "geometrias": {}}

    names = {str(v["nome_via"]) for v in top}
    buckets: dict[str, list[list[tuple[float, float]]]] = {n: [] for n in names}

    for feat in features or []:
        if not isinstance(feat, dict):
            continue
        props = feat.get("properties") if isinstance(feat.get("properties"), dict) else {}
        nome = _normalize_street_name(props.get("street_name"))
        if not nome or nome not in buckets:
            continue
        coords = _coords_from_geometry(feat.get("geometry") if isinstance(feat.get("geometry"), dict) else None)
        if len(coords) >= 2:
            buckets[nome].append(coords)

    geometrias: dict[str, dict] = {}
    for v in top:
        nome = str(v["nome_via"])
        segs = buckets.get(nome) or []
        merged: list[tuple[float, float]] = []
        for seg in segs:
            if merged and seg and merged[-1] == seg[0]:
                merged.extend(seg[1:])
            else:
                merged.extend(seg)
        # Dedup consecutivos
        dedup: list[tuple[float, float]] = []
        for pt in merged:
            if not dedup or dedup[-1] != pt:
                dedup.append(pt)
        slim = _downsample(dedup, max_pts_per_via)
        geometrias[nome] = {
            "coords": [[lon, lat] for lon, lat in slim],
            "fluxo_score": v.get("fluxo_score"),
            "concorrentes_no_trecho": v.get("concorrentes_no_trecho", 0),
            "n_segments": len(segs),
        }

    com_geo = sum(1 for g in geometrias.values() if len(g.get("coords") or []) >= 2)
    return {
        "status": "ok" if com_geo else "indisponivel",
        "motivo": None if com_geo else "features sem geometria casada às vias",
        "geometrias": geometrias,
        "n_com_geometria": com_geo,
    }


def render_mapa_vias_svg(
    geometrias: dict[str, dict] | None,
    lat: float,
    lng: float,
    *,
    width: float = 560.0,
    height: float = 300.0,
) -> str | None:
    """SVG self-contained: vias coloridas por fluxo_score + centroide."""
    if not isinstance(geometrias, dict) or not geometrias:
        return None
    try:
        lat_f, lng_f = float(lat), float(lng)
    except (TypeError, ValueError):
        return None

    xs: list[float] = [lng_f]
    ys: list[float] = [lat_f]
    paths: list[tuple[str, list[tuple[float, float]], float | int | None]] = []
    for nome, g in geometrias.items():
        if not isinstance(g, dict):
            continue
        raw = g.get("coords") or []
        pts: list[tuple[float, float]] = []
        for pt in raw:
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                try:
                    lon, la = float(pt[0]), float(pt[1])
                except (TypeError, ValueError):
                    continue
                pts.append((lon, la))
                xs.append(lon)
                ys.append(la)
        if len(pts) >= 2:
            paths.append((str(nome), pts, g.get("fluxo_score")))

    if not paths:
        return None

    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    pad = 12.0
    dx = (maxx - minx) or 1e-5
    dy = (maxy - miny) or 1e-5
    # Margem 8% para não colar nas bordas
    minx -= dx * 0.08
    maxx += dx * 0.08
    miny -= dy * 0.08
    maxy += dy * 0.08
    dx = (maxx - minx) or 1e-5
    dy = (maxy - miny) or 1e-5
    sc = min((width - 2 * pad) / dx, (height - 2 * pad) / dy)

    def _px(lon: float, la: float) -> tuple[float, float]:
        return (pad + (lon - minx) * sc, pad + (maxy - la) * sc)

    partes = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" '
        f'style="width:100%;border:1px solid #E2E8F0;border-radius:4px;background:#F8FAFC;">'
    ]
    # Ordena: fluxo baixo primeiro (top fica por cima)
    paths_sorted = sorted(
        paths,
        key=lambda x: float(x[2] or 0),
    )
    for nome, pts, score in paths_sorted:
        cor = _cor_fluxo(score)
        sw = 4.5 if float(score or 0) >= 85 else (3.2 if float(score or 0) >= 60 else 2.2)
        d = " ".join(
            f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}"
            for i, (x, y) in enumerate(_px(lon, la) for lon, la in pts)
        )
        safe = (
            nome.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
        partes.append(
            f'<path d="{d}" fill="none" stroke="{cor}" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round" opacity="0.92">'
            f"<title>{safe} · fluxo {score}</title></path>"
        )

    cx, cy = _px(lng_f, lat_f)
    partes.append(
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="#0F172A" '
        f'stroke="#fff" stroke-width="2"/>'
    )
    # Legenda compacta
    partes.append(
        f'<text x="{pad:.0f}" y="{height - 6:.0f}" font-size="9" fill="#64748B" '
        f'font-family="system-ui,sans-serif">Vermelho = maior fluxo · ponto = centróide/candidato · OSM</text>'
    )
    partes.append("</svg>")
    return "".join(partes)


def anexar_geometria_e_mapa(
    top_vias: list[dict],
    features: list[dict] | None,
    lat: float,
    lng: float,
) -> str | None:
    """Anexa `coords` slim em cada via + devolve `mapa_svg` (ou None)."""
    try:
        exported = expor_geometria_vias(features, top_vias)
        geos = exported.get("geometrias") if isinstance(exported, dict) else {}
        if not isinstance(geos, dict):
            return None
        for v in top_vias:
            if not isinstance(v, dict):
                continue
            g = geos.get(str(v.get("nome_via") or ""))
            if isinstance(g, dict) and g.get("coords"):
                v["coords"] = g["coords"]
                v["n_segments_geo"] = g.get("n_segments")
        return render_mapa_vias_svg(geos, lat, lng)
    except Exception:
        logger.warning("anexar_geometria_e_mapa falhou", exc_info=True)
        return None
