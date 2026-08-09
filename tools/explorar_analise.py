"""Light /explorar analyze: pin + lente → Maps rivals + Absorção (no composite score)."""
from __future__ import annotations

import re
from typing import Any, Literal

from tools.absorcao_margem_fresca import absorcao_margem_fresca
from tools.listing_candidato_normalize import _haversine_m
from tools.voronoi_atratividade import extract_place_xy

Lente = Literal["500m", "1km", "bairro"]
_MAX_RIVALS_REVIEWS = 5
_MAX_RECLAMACOES = 5

_LENTE_M = {"500m": 500, "1km": 1000}
_AREA_M = {
    "academia": 1150.0,
    "crossfit_box": 650.0,
    "studio_pilates": 215.0,
    "studio_funcional": 475.0,
    "outro": 900.0,
}
_TIPOS_OK = frozenset(_AREA_M)

_SEGMENTOS = (
    ("15-24", "h_15_24", "m_15_24"),
    ("25-39", "h_25_39", "m_25_39"),
    ("40-59", "h_40_59", "m_40_59"),
    ("60+", "h_60_mais", "m_60_mais"),
)


def _in_lente(
    *,
    lat: float,
    lng: float,
    pin_lat: float,
    pin_lng: float,
    lente: str,
    ring: list[tuple[float, float]] | None,
) -> bool:
    if lente == "bairro" and ring and len(ring) >= 3:
        from tools.bairro_poligono import point_in_ring

        return point_in_ring(lng, lat, ring)
    raio = _LENTE_M.get(lente, 1000)
    return _haversine_m(pin_lat, pin_lng, lat, lng) <= raio


def _segmentos_from_setores(setores: list[dict[str, Any]]) -> dict[str, Any]:
    segs: dict[str, Any] = {}
    for faixa, h_k, m_k in _SEGMENTOS:
        h = sum(int(s.get(h_k) or 0) for s in setores)
        m = sum(int(s.get(m_k) or 0) for s in setores)
        segs[faixa] = {"h": h, "m": m, "total": h + m}
    return segs


def _normalize_rival(raw: dict[str, Any], pin_lat: float, pin_lng: float) -> dict[str, Any] | None:
    la, lo = extract_place_xy(raw)
    if la is None or lo is None:
        return None
    nome = (
        raw.get("nome")
        or raw.get("title")
        or (raw.get("displayName") or {}).get("text")
        or ""
    )
    reviews = raw.get("reviews")
    if reviews is None:
        reviews = raw.get("userRatingCount") or raw.get("user_ratings_total") or 0
    tipos = raw.get("tipos") or raw.get("types") or []
    if not isinstance(tipos, list):
        tipos = []
    end = (
        raw.get("endereco")
        or raw.get("formattedAddress")
        or raw.get("address")
        or ""
    )
    pid = str(raw.get("place_id") or raw.get("id") or "").strip()
    data_id = str(raw.get("data_id") or "").strip()
    return {
        "nome": str(nome).strip() or "Academia",
        "lat": la,
        "lng": lo,
        "dist_m": int(round(_haversine_m(pin_lat, pin_lng, la, lo))),
        "rating": raw.get("rating"),
        "reviews": int(reviews or 0),
        "tipos": tipos,
        "endereco": str(end).strip(),
        "place_id": pid,
        "data_id": data_id,
        "reclamacoes": [],
    }


def _base_label(*, lente: str, bairro: str | None, ring: list | None) -> str:
    if lente == "bairro":
        nome = (bairro or "bairro").strip() or "bairro"
        if ring and len(ring) >= 3:
            return f"Recorte do bairro {nome} · IBGE Censo 2022"
        return f"Recorte do bairro {nome} indisponível · raio 1 km · IBGE Censo 2022"
    if lente == "500m":
        return "Raio 500 m a partir do centro do bairro · IBGE Censo 2022"
    return "Raio 1 km a partir do centro do bairro · IBGE Censo 2022"


def _id_municipio(cidade: str | None, uf: str | None) -> str | None:
    if not cidade:
        return None
    try:
        from tools.ibge_tools import buscar_municipio

        hit = buscar_municipio(cidade, uf or "")
    except Exception:
        return None
    if isinstance(hit, dict) and hit.get("codigo"):
        return str(hit["codigo"])
    return None


def parse_publico_alvo_idades(publico_alvo: str | None) -> tuple[int | None, int | None]:
    raw = (publico_alvo or "").strip()
    m = re.match(r"^(\d+)\s*-\s*(\d+)$", raw)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.match(r"^(\d+)\s*\+$", raw)
    if m:
        return int(m.group(1)), 120
    return None, None


def _bbox_ring(lat: float, lng: float, raio_m: float) -> list[tuple[float, float]]:
    import math

    dlat = raio_m / 111_320.0
    dlng = raio_m / (111_320.0 * max(0.2, math.cos(math.radians(lat))))
    return [
        (lng - dlng, lat - dlat),
        (lng + dlng, lat - dlat),
        (lng + dlng, lat + dlat),
        (lng - dlng, lat + dlat),
        (lng - dlng, lat - dlat),
    ]


def _resolve_ring(
    *,
    lente: str,
    bairro: str | None,
    cidade: str | None,
    uf: str | None,
    injected: list[tuple[float, float]] | None,
) -> list[tuple[float, float]] | None:
    if injected and len(injected) >= 3:
        return injected
    if lente != "bairro" or not bairro:
        return None
    idm = _id_municipio(cidade, uf)
    if not idm:
        return None
    try:
        from tools.bairro_poligono import resolver_bairro_poligono

        bp = resolver_bairro_poligono(
            id_municipio=idm, bairro=bairro, cidade=cidade, uf=uf
        )
    except Exception:
        return None
    ring = (bp or {}).get("ring") if isinstance(bp, dict) else None
    return ring if isinstance(ring, list) and len(ring) >= 3 else None


def _load_setores(
    *,
    injected: list[dict[str, Any]] | None,
    ring: list[tuple[float, float]] | None,
    pin_lat: float,
    pin_lng: float,
    lente: str,
    cidade: str | None = None,
    uf: str | None = None,
) -> list[dict[str, Any]]:
    if injected is not None:
        rows = list(injected)
    else:
        rows = []
        idm = _id_municipio(cidade, uf)
        query_ring = ring if ring and len(ring) >= 3 else _bbox_ring(
            pin_lat, pin_lng, float(_LENTE_M.get(lente, 1000)) + 250.0
        )
        if idm:
            try:
                from tools.censo_setor_tools import carregar_setores_idade_sexo

                rows = list(carregar_setores_idade_sexo(idm, ring=query_ring) or [])
            except Exception:
                rows = []
    out: list[dict[str, Any]] = []
    for s in rows:
        if not isinstance(s, dict):
            continue
        sl, sg = s.get("lat"), s.get("lng")
        if sl is None or sg is None:
            continue
        if _in_lente(
            lat=float(sl),
            lng=float(sg),
            pin_lat=pin_lat,
            pin_lng=pin_lng,
            lente=lente if (lente != "bairro" or (ring and len(ring) >= 3)) else "1km",
            ring=ring,
        ):
            out.append(s)
    return out


def _maybe_voronoi(
    *,
    pin_lat: float,
    pin_lng: float,
    rivals: list[dict[str, Any]],
    ring: list[tuple[float, float]] | None,
    setores: list[dict[str, Any]],
    absorcao: dict[str, Any],
) -> dict[str, Any]:
    try:
        from tools.voronoi_atratividade import compute_voronoi_smoke

        sites = [
            {
                "lat": pin_lat,
                "lng": pin_lng,
                "is_candidato": True,
                "peso": float(absorcao.get("area_candidato_m2") or 1500),
            }
        ]
        for r in rivals:
            sites.append(
                {
                    "lat": r["lat"],
                    "lng": r["lng"],
                    "is_candidato": False,
                    "peso": 1500.0,
                }
            )
        pop = int(sum(int(s.get("pessoas") or 0) for s in setores))
        return compute_voronoi_smoke(
            sites=sites,
            ring=ring,
            setores=setores,
            pool_ref=int(absorcao.get("pool_primario") or 0),
            pop_bairro=pop,
            pin_fonte="candidato_latlng",
        )
    except Exception:
        return {
            "status": "indisponivel",
            "motivo": "erro_interno",
            "carimbo": "indisponivel · erro_interno · voronoi_smoke · n/a",
        }


def _reclamacoes_baixa_nota(place_id: str, data_id: str | None = None) -> list[dict[str, Any]]:
    if not place_id:
        return []
    try:
        from tools.explorar_reviews import fetch_explorar_reviews

        raw = fetch_explorar_reviews(place_id=place_id, data_id=data_id)
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for rev in raw:
        try:
            rating = int(float(rev.get("rating") or 5))
        except (TypeError, ValueError):
            continue
        if rating > 3:
            continue
        texto = (
            rev.get("text")
            or rev.get("snippet")
            or rev.get("quote_curta")
            or rev.get("description")
            or ""
        ).strip()
        if not texto:
            continue
        user_raw = rev.get("user")
        if isinstance(user_raw, dict):
            autor = str(user_raw.get("name") or "Anônimo")
        else:
            autor = str(rev.get("autor") or "Anônimo")
        out.append({"texto": texto[:180], "rating": rating, "autor": autor[:60]})
        if len(out) >= _MAX_RECLAMACOES:
            break
    return out


def _enrich_rivals_reclamacoes(rivals: list[dict[str, Any]]) -> None:
    n = 0
    for r in rivals:
        if n >= _MAX_RIVALS_REVIEWS:
            break
        pid = str(r.get("place_id") or "").strip()
        if not pid:
            continue
        r["reclamacoes"] = _reclamacoes_baixa_nota(pid, str(r.get("data_id") or "") or None)
        n += 1


def _fetch_maps_rivals(
    *,
    tipo_negocio: str,
    cidade: str | None,
    bairro: str | None,
    uf: str | None,
    lat: float | None = None,
    lng: float | None = None,
) -> list[dict[str, Any]]:
    try:
        from tools.competitor_tools import _query_formato1, _searchapi_maps_textsearch
    except Exception:
        return []
    query = _query_formato1(tipo_negocio, bairro or "", cidade or "", uf or "")
    region = ", ".join(p for p in (cidade, uf, "Brasil") if p)
    try:
        return list(
            _searchapi_maps_textsearch(
                query,
                max_results=40,
                region=region,
                lat=lat,
                lng=lng,
            )
            or []
        )
    except Exception:
        return []


def run_explorar_analise(
    *,
    lat: float,
    lng: float,
    lente: Lente,
    cidade: str | None = None,
    bairro: str | None = None,
    uf: str | None = None,
    endereco: str | None = None,
    tipo_negocio: str = "academia",
    area_candidato_m2: float | None = None,
    publico_alvo: str | None = None,
    idade_min: int | None = None,
    idade_max: int | None = None,
    _concorrentes: list[dict] | None = None,
    _setores: list[dict] | None = None,
    _ring: list[tuple[float, float]] | None = None,
) -> dict[str, Any]:
    pin_lat, pin_lng = float(lat), float(lng)
    if endereco and (not cidade or not bairro):
        from tools.explorar_pin import parse_lugar_explorar

        lugar = parse_lugar_explorar(endereco)
        bairro = bairro or lugar.get("bairro")
        cidade = cidade or lugar.get("cidade")
        uf = uf or lugar.get("uf")
    lente_s: str = lente if lente in ("500m", "1km", "bairro") else "1km"
    tn = (tipo_negocio or "academia").strip().lower()
    if tn not in _TIPOS_OK:
        tn = "academia"
    area = float(area_candidato_m2) if area_candidato_m2 else _AREA_M[tn]
    if idade_min is None or idade_max is None:
        lo, hi = parse_publico_alvo_idades(publico_alvo)
        if idade_min is None:
            idade_min = lo
        if idade_max is None:
            idade_max = hi
    ring = _resolve_ring(
        lente=lente_s,
        bairro=bairro,
        cidade=cidade,
        uf=uf,
        injected=_ring,
    )
    lente_filter = lente_s
    if lente_s == "bairro" and (not ring or len(ring) < 3):
        lente_filter = "1km"

    if _concorrentes is not None:
        raw_rivals = list(_concorrentes)
    else:
        raw_rivals = _fetch_maps_rivals(
            tipo_negocio=tn,
            cidade=cidade,
            bairro=bairro,
            uf=uf,
            lat=pin_lat,
            lng=pin_lng,
        )
    rivals: list[dict[str, Any]] = []
    for raw in raw_rivals:
        if not isinstance(raw, dict):
            continue
        item = _normalize_rival(raw, pin_lat, pin_lng)
        if item is None:
            continue
        if _in_lente(
            lat=item["lat"],
            lng=item["lng"],
            pin_lat=pin_lat,
            pin_lng=pin_lng,
            lente=lente_filter,
            ring=ring if lente_s == "bairro" else None,
        ):
            rivals.append(item)
    try:
        from tools.competitor_tools import _filtrar_status_operacional, _tipo_relevante

        rivals = _filtrar_status_operacional(rivals)
        rivals = [r for r in rivals if _tipo_relevante(r, tn)]
    except Exception:
        pass
    rivals.sort(key=lambda r: r["dist_m"])
    _enrich_rivals_reclamacoes(rivals)

    setores = _load_setores(
        injected=_setores,
        ring=ring if lente_s == "bairro" else None,
        pin_lat=pin_lat,
        pin_lng=pin_lng,
        lente=lente_filter,
        cidade=cidade,
        uf=uf,
    )
    segmentos = _segmentos_from_setores(setores) if setores else None
    pop = int(sum(int(s.get("pessoas") or 0) for s in setores))
    fonte_espacial = (
        "poligono_ibge" if lente_s == "bairro" and ring and len(ring) >= 3 else "raio_fallback"
    )
    label = _base_label(lente=lente_s, bairro=bairro, ring=ring)
    absorcao = absorcao_margem_fresca(
        concorrentes=rivals,
        pop_poligono=pop,
        area_candidato_m2=area,
        modelo_cenario="mid",
        fonte_espacial=fonte_espacial,
        censo_base="IBGE Censo 2022",
        segmentos=segmentos,
        idade_min=idade_min,
        idade_max=idade_max,
    )
    from tools.explorar_leitura import carimbos_explorar, leituras_absorcao

    absorcao["leituras"] = leituras_absorcao(absorcao)
    absorcao["fontes"] = carimbos_explorar(label=label)
    absorcao["voronoi_smoke"] = _maybe_voronoi(
        pin_lat=pin_lat,
        pin_lng=pin_lng,
        rivals=rivals,
        ring=ring,
        setores=setores,
        absorcao=absorcao,
    )
    return {
        "lente": lente_s,
        "tipo_negocio": tn,
        "base_espacial_label": label,
        "pin": {"lat": pin_lat, "lng": pin_lng},
        "concorrentes": rivals,
        "absorcao_margem_fresca": absorcao,
        "carimbo_base": f"{len(rivals)} rivais · {label} · SearchAPI Maps · {tn}",
        "cidade": cidade,
        "bairro": bairro,
        "uf": uf,
    }
