"""Voronoi smoke — clássico + ponderado; pool preferencialmente via pirâmide na célula."""
from __future__ import annotations

import math
from typing import Any

_SEGMENTOS_COLS = (
    ("15-24", "h_15_24", "m_15_24"),
    ("25-39", "h_25_39", "m_25_39"),
    ("40-59", "h_40_59", "m_40_59"),
    ("60+", "h_60_mais", "m_60_mais"),
)


def _indisponivel(
    motivo: str,
    *,
    pool_ref: int | None = None,
    pop_bairro: int | None = None,
    n_sites: int = 0,
) -> dict[str, Any]:
    return {
        "status": "indisponivel",
        "motivo": motivo,
        "pop_bairro": pop_bairro,
        "pop_celula": None,
        "pop_celula_ponderada": None,
        "pool_ref": pool_ref,
        "pool_voronoi": None,
        "pool_voronoi_ponderado": None,
        "delta_pct": None,
        "n_sites": n_sites,
        "n_setores_celula": None,
        "peso_candidato": None,
        "metodo_pool": None,
        "estoque_primario_celula": None,
        "pin_fonte": None,
        "carimbo": f"indisponivel · {motivo} · voronoi_smoke · n/a",
    }


def _finite(x: Any) -> bool:
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def _dist2(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    # Local planar OK for bairro-scale smoke (degrees²).
    dy = lat1 - lat2
    dx = lng1 - lng2
    return dx * dx + dy * dy


def _point_in_ring(lon: float, lat: float, ring: list[tuple[float, float]]) -> bool:
    from tools.bairro_poligono import point_in_ring

    return point_in_ring(lon, lat, ring)


def _normalize_sites(sites: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for s in sites or []:
        if not isinstance(s, dict):
            continue
        lat, lng = s.get("lat"), s.get("lng")
        if not _finite(lat) or not _finite(lng):
            continue
        peso = s.get("peso")
        try:
            w = float(peso) if peso is not None else 1500.0
        except (TypeError, ValueError):
            w = 1500.0
        if w <= 0:
            w = 1500.0
        out.append(
            {
                "lat": float(lat),
                "lng": float(lng),
                "peso": w,
                "is_candidato": bool(s.get("is_candidato")),
            }
        )
    return out


def _nearest_index(
    lat: float,
    lng: float,
    sites: list[dict[str, Any]],
    *,
    weighted: bool,
) -> int:
    best_i = 0
    best = float("inf")
    for i, s in enumerate(sites):
        d2 = _dist2(lat, lng, s["lat"], s["lng"])
        if weighted:
            # Multiplicatively weighted: d / sqrt(w) → compare d² / w
            score = d2 / float(s["peso"])
        else:
            score = d2
        if score < best:
            best = score
            best_i = i
    return best_i


def _row_has_idade(row: dict[str, Any]) -> bool:
    for _, hc, mc in _SEGMENTOS_COLS:
        if row.get(hc) is not None or row.get(mc) is not None:
            return True
    return False


def _segmentos_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    if not any(_row_has_idade(r) for r in rows):
        return None
    segmentos: dict[str, Any] = {}
    for label, hc, mc in _SEGMENTOS_COLS:
        h = sum(int(r.get(hc) or 0) for r in rows)
        m = sum(int(r.get(mc) or 0) for r in rows)
        t = h + m
        if t <= 0:
            continue
        segmentos[label] = {
            "homens": h,
            "mulheres": m,
            "total": t,
            "pct_homens": round(100 * h / t, 1),
            "pct_mulheres": round(100 * m / t, 1),
        }
    return segmentos or None


def _pool_from_segmentos(
    segmentos: dict[str, Any],
    *,
    renda_pc: float | None,
    perfil_ab: bool | None,
    idade_min: int | None,
    idade_max: int | None,
) -> tuple[int, int, str]:
    """Return (pool_primario, estoque_primario, pen_key)."""
    from tools.absorcao_margem_fresca import (
        _estoque_faixas,
        _penetracao_efetiva,
        faixas_primario_from_idade,
    )
    from tools.parametros_metodologia import param

    interesse = float(param("penetracao_potencial_fitness"))
    pen, pen_key = _penetracao_efetiva(renda_pc, perfil_ab)
    imin = int(idade_min if idade_min is not None else param("publico_fitness_idade_min"))
    imax = int(idade_max if idade_max is not None else param("publico_fitness_idade_max"))
    prim = faixas_primario_from_idade(imin, imax)
    est = _estoque_faixas(segmentos, prim)
    pool = int(round(est * interesse * pen))
    return pool, est, pen_key


def extract_place_xy(place: dict[str, Any]) -> tuple[float | None, float | None]:
    """lat/lng de concorrente Maps (top-level ou gps_coordinates SearchAPI)."""
    if not isinstance(place, dict):
        return None, None
    if _finite(place.get("lat")) and _finite(place.get("lng")):
        return float(place["lat"]), float(place["lng"])
    if _finite(place.get("latitude")) and _finite(place.get("longitude")):
        return float(place["latitude"]), float(place["longitude"])
    gps = place.get("gps_coordinates")
    if isinstance(gps, dict):
        la, lo = gps.get("latitude"), gps.get("longitude")
        if _finite(la) and _finite(lo):
            return float(la), float(lo)
    loc = place.get("location")
    if isinstance(loc, dict):
        if _finite(loc.get("lat")) and _finite(loc.get("lng")):
            return float(loc["lat"]), float(loc["lng"])
        if _finite(loc.get("latitude")) and _finite(loc.get("longitude")):
            return float(loc["latitude"]), float(loc["longitude"])
    return None, None


def concorrentes_from_searchapi_local_results(
    payload: dict[str, Any] | list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Converte `local_results` SearchAPI Maps → lista com lat/lng top-level."""
    rows = payload
    if isinstance(payload, dict):
        rows = payload.get("local_results") or []
    out: list[dict[str, Any]] = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        la, lo = extract_place_xy(r)
        if la is None or lo is None:
            continue
        item = dict(r)
        item["lat"] = la
        item["lng"] = lo
        item["nome"] = r.get("nome") or r.get("title")
        item["gate_espacial"] = r.get("gate_espacial") or "raio_fallback"
        out.append(item)
    return out


def _ring_centroid(ring: list[tuple[float, float]]) -> tuple[float, float] | None:
    if not ring or len(ring) < 3:
        return None
    # ring pts are (lon, lat); close ring may duplicate first point
    pts = ring[:-1] if ring[0] == ring[-1] and len(ring) > 3 else ring
    if not pts:
        return None
    lon = sum(p[0] for p in pts) / len(pts)
    lat = sum(p[1] for p in pts) / len(pts)
    return lat, lon


def compute_voronoi_smoke(
    *,
    sites: list[dict[str, Any]],
    ring: list[tuple[float, float]] | None,
    setores: list[dict[str, Any]],
    pool_ref: int,
    pop_bairro: int,
    renda_pc: float | None = None,
    perfil_ab: bool | None = None,
    idade_min: int | None = None,
    idade_max: int | None = None,
    pin_fonte: str | None = None,
) -> dict[str, Any]:
    """Célula = setores no ring cujo site mais próximo é o candidato (Voronoi).

    Clássico: distância euclidiana local. Ponderado: d/sqrt(peso) com peso=area_proxy.
    Preferência: pool = estoque_form(célula) × interesse × pen (pirâmide).
    Fallback: escala pool_ref × pop_célula / pop_bairro.
    Pin da unidade: explícito ou centróide do bairro — nunca listing A1.
    """
    pool_i = int(pool_ref)
    pop_b = int(pop_bairro)
    if not ring or len(ring) < 3:
        return _indisponivel("sem_poligono", pool_ref=pool_i, pop_bairro=pop_b)

    norm = _normalize_sites(sites)
    cands = [i for i, s in enumerate(norm) if s["is_candidato"]]
    if not cands:
        return _indisponivel("sem_coords", pool_ref=pool_i, pop_bairro=pop_b, n_sites=len(norm))
    if len(norm) < 2:
        return _indisponivel("poucos_pontos", pool_ref=pool_i, pop_bairro=pop_b, n_sites=len(norm))

    cand_i = cands[0]
    peso_cand = float(norm[cand_i]["peso"])
    if pop_b <= 0:
        return _indisponivel("sem_setores", pool_ref=pool_i, pop_bairro=pop_b, n_sites=len(norm))
    if not setores:
        return _indisponivel("sem_setores", pool_ref=pool_i, pop_bairro=pop_b, n_sites=len(norm))

    cell_classic: list[dict[str, Any]] = []
    cell_weighted: list[dict[str, Any]] = []
    pop_c = 0
    pop_w = 0
    for row in setores or []:
        if not isinstance(row, dict):
            continue
        la, lo = row.get("lat"), row.get("lng")
        if not _finite(la) or not _finite(lo):
            continue
        lat, lng = float(la), float(lo)
        if not _point_in_ring(lng, lat, ring):
            continue
        try:
            pessoas = int(row.get("pessoas") or 0)
        except (TypeError, ValueError):
            pessoas = 0
        if pessoas <= 0:
            continue
        if _nearest_index(lat, lng, norm, weighted=False) == cand_i:
            cell_classic.append(row)
            pop_c += pessoas
        if _nearest_index(lat, lng, norm, weighted=True) == cand_i:
            cell_weighted.append(row)
            pop_w += pessoas

    n_set = len(cell_classic)
    segs_c = _segmentos_from_rows(cell_classic)
    segs_w = _segmentos_from_rows(cell_weighted)

    estoque_c: int | None = None
    if segs_c is not None:
        pool_v, estoque_c, pen_key = _pool_from_segmentos(
            segs_c,
            renda_pc=renda_pc,
            perfil_ab=perfil_ab,
            idade_min=idade_min,
            idade_max=idade_max,
        )
        metodo = "piramide_celula"
        if segs_w is not None:
            pool_vp, _, _ = _pool_from_segmentos(
                segs_w,
                renda_pc=renda_pc,
                perfil_ab=perfil_ab,
                idade_min=idade_min,
                idade_max=idade_max,
            )
        else:
            pool_vp = int(round(pool_i * pop_w / pop_b)) if pop_b else 0
        carimbo = (
            f"{pool_v} · estoque_form_célula×interesse×{pen_key} · "
            f"Voronoi clássico∩IBGE pirâmide · smoke"
        )
    else:
        pool_v = int(round(pool_i * pop_c / pop_b))
        pool_vp = int(round(pool_i * pop_w / pop_b))
        metodo = "escala_pop"
        carimbo = (
            f"{pool_v} · escala_pool×pop_célula/pop_bairro · Voronoi clássico∩IBGE · smoke"
        )

    delta = (pool_v - pool_i) / pool_i if pool_i else None

    return {
        "status": "ok",
        "motivo": None,
        "pop_bairro": pop_b,
        "pop_celula": pop_c,
        "pop_celula_ponderada": pop_w,
        "pool_ref": pool_i,
        "pool_voronoi": pool_v,
        "pool_voronoi_ponderado": pool_vp,
        "delta_pct": delta,
        "n_sites": len(norm),
        "n_setores_celula": n_set,
        "peso_candidato": peso_cand,
        "metodo_pool": metodo,
        "estoque_primario_celula": estoque_c,
        "pin_fonte": pin_fonte,
        "carimbo": carimbo,
    }


def sites_from_state(
    state: dict[str, Any],
    absorcao: dict[str, Any],
) -> dict[str, Any]:
    """Monta kwargs de compute_voronoi_smoke.

    Rivais = lat/lng dos concorrentes (Maps/SearchAPI).
    Pin da unidade = candidato_lat/lng explícito OU centróide do polígono —
    **nunca** listing A1 / geoscout.
    """
    from tools.matriz_demo_saturacao import classificar_tier_concorrente, concorrentes_espaciais_from_state
    from tools.parametros_metodologia import param

    def _proxy(tier: str) -> float:
        key = {
            "low": "area_proxy_low_m2",
            "mid": "area_proxy_mid_m2",
            "premium": "area_proxy_premium_m2",
            "nicho": "area_proxy_nicho_desconhecido_m2",
            "desconhecido": "area_proxy_nicho_desconhecido_m2",
        }.get(tier, "area_proxy_mid_m2")
        return float(param(key))

    ring = _ring_from_state(state)
    id_mun = _id_municipio_from_state(state)

    if ring is None and id_mun:
        try:
            from tools.bairro_poligono import resolver_bairro_poligono

            ip0 = state.get("input_params") if isinstance(state.get("input_params"), dict) else {}
            demo0 = state.get("demografia_bairro") if isinstance(state.get("demografia_bairro"), dict) else {}
            poly = resolver_bairro_poligono(
                id_municipio=id_mun,
                bairro=str(ip0.get("bairro") or state.get("bairro") or demo0.get("bairro") or ""),
                cidade=str(ip0.get("cidade") or state.get("cidade") or ""),
                uf=str(ip0.get("uf") or state.get("uf") or "") or None,
            )
            if poly and isinstance(poly.get("ring"), list):
                ring = []
                for pt in poly["ring"]:
                    if isinstance(pt, (list, tuple)) and len(pt) >= 2 and _finite(pt[0]) and _finite(pt[1]):
                        ring.append((float(pt[0]), float(pt[1])))
                if len(ring) < 3:
                    ring = None
        except Exception:
            ring = ring

    modelo = str(absorcao.get("modelo_teto") or "mid")
    sites: list[dict[str, Any]] = []
    pin_fonte: str | None = None

    clat, clng = _candidato_xy_explicito(state)
    if clat is not None and clng is not None:
        pin_fonte = "explicito"
    else:
        cen = _ring_centroid(ring) if ring else None
        if cen is not None:
            clat, clng = cen
            pin_fonte = "centroide_bairro"

    if clat is not None and clng is not None:
        sites.append(
            {
                "lat": clat,
                "lng": clng,
                "peso": _proxy(modelo if modelo in ("low", "mid", "premium") else "mid"),
                "is_candidato": True,
            }
        )

    cs, _ = concorrentes_espaciais_from_state(state)
    for c in cs:
        if not isinstance(c, dict):
            continue
        la, lo = extract_place_xy(c)
        if la is None or lo is None:
            continue
        if clat is not None and abs(float(la) - clat) < 1e-6 and abs(float(lo) - clng) < 1e-6:
            continue
        tier = classificar_tier_concorrente(c)
        t = tier if tier in ("low", "mid", "premium", "nicho", "desconhecido") else "desconhecido"
        sites.append(
            {
                "lat": float(la),
                "lng": float(lo),
                "peso": _proxy("nicho" if t == "desconhecido" else t),
                "is_candidato": False,
            }
        )

    inject = state.get("_voronoi_setores_rows")
    inject_list = inject if isinstance(inject, list) else None
    setores = state.get("_voronoi_setores")
    if not isinstance(setores, list) or not setores:
        from tools.censo_setor_tools import carregar_setores_censo, carregar_setores_idade_sexo

        idade_rows = carregar_setores_idade_sexo(
            id_mun,
            ring=ring,
            _rows=inject_list,
        )
        if idade_rows:
            setores = idade_rows
        else:
            setores = carregar_setores_censo(
                id_mun,
                ring=ring,
                _rows=inject_list,
            )

    demo = state.get("demografia_bairro") if isinstance(state.get("demografia_bairro"), dict) else {}
    pop_b = demo.get("populacao")
    try:
        pop_bairro = int(pop_b) if pop_b is not None else int(absorcao.get("estoque_primario") or 0)
    except (TypeError, ValueError):
        pop_bairro = 0

    pool_ref = int(absorcao.get("pool_primario") or absorcao.get("pool_demografico") or 0)

    ip = state.get("input_params") if isinstance(state.get("input_params"), dict) else {}
    renda_pc = demo.get("renda_per_capita") or demo.get("renda_pc") or ip.get("renda_pc")
    try:
        renda_f = float(renda_pc) if renda_pc is not None else None
    except (TypeError, ValueError):
        renda_f = None

    idade_min = absorcao.get("idade_min")
    idade_max = absorcao.get("idade_max")
    if idade_min is None:
        idade_min = ip.get("idade_min") or state.get("idade_min")
    if idade_max is None:
        idade_max = ip.get("idade_max") or state.get("idade_max")
    try:
        imin = int(idade_min) if idade_min is not None else None
    except (TypeError, ValueError):
        imin = None
    try:
        imax = int(idade_max) if idade_max is not None else None
    except (TypeError, ValueError):
        imax = None

    return {
        "sites": sites,
        "ring": ring,
        "setores": setores if isinstance(setores, list) else [],
        "pool_ref": pool_ref,
        "pop_bairro": pop_bairro if pop_bairro > 0 else pool_ref,
        "renda_pc": renda_f,
        "perfil_ab": None,
        "idade_min": imin,
        "idade_max": imax,
        "pin_fonte": pin_fonte,
    }


def _id_municipio_from_state(state: dict[str, Any]) -> str | None:
    for key in ("id_municipio", "codigo_ibge", "codigo_municipio"):
        v = state.get(key)
        if v:
            return str(v)
    for blk_key in ("input_params", "demografia_bairro", "market_context"):
        blk = state.get(blk_key)
        if not isinstance(blk, dict):
            continue
        for key in ("id_municipio", "codigo_ibge", "codigo_municipio", "id_ibge"):
            v = blk.get(key)
            if v:
                return str(v)
        mun = blk.get("municipio")
        if isinstance(mun, dict) and mun.get("codigo"):
            return str(mun["codigo"])
    # Resolve via cidade/UF se possível
    ip = state.get("input_params") if isinstance(state.get("input_params"), dict) else {}
    cidade = ip.get("cidade") or state.get("cidade")
    uf = ip.get("uf") or state.get("uf")
    if cidade and uf:
        try:
            from tools.ibge_tools import buscar_municipio

            mun = buscar_municipio(str(cidade), str(uf))
            if mun and mun.get("codigo"):
                return str(mun["codigo"])
        except Exception:
            pass
    return None


def _candidato_xy_explicito(state: dict[str, Any]) -> tuple[float | None, float | None]:
    """Só pin explícito (form futuro / override). Nunca listing A1/geoscout."""
    if _finite(state.get("candidato_lat")) and _finite(state.get("candidato_lng")):
        return float(state["candidato_lat"]), float(state["candidato_lng"])
    ip = state.get("input_params") if isinstance(state.get("input_params"), dict) else {}
    if _finite(ip.get("candidato_lat")) and _finite(ip.get("candidato_lng")):
        return float(ip["candidato_lat"]), float(ip["candidato_lng"])
    return None, None


def _ring_from_state(state: dict[str, Any]) -> list[tuple[float, float]] | None:
    bp = state.get("bairro_poligono")
    if isinstance(bp, dict):
        ring = bp.get("ring")
        if isinstance(ring, list) and len(ring) >= 3:
            out: list[tuple[float, float]] = []
            for pt in ring:
                if isinstance(pt, (list, tuple)) and len(pt) >= 2 and _finite(pt[0]) and _finite(pt[1]):
                    out.append((float(pt[0]), float(pt[1])))
            if len(out) >= 3:
                return out
    return None
