"""
Censo 2022 por setor censitário (BigQuery basedosdados) — demografia de BAIRRO.

Bairro não é unidade censitária. Agregamos os SETORES censitários num raio do
centróide do bairro (ST_DWITHIN) → população, domicílios e MÉDIA DE MORADORES reais
do bairro. Censo 2022 não tem renda por setor (IBGE não liberou) — renda vem do CKAN
(ver bairro_renda_loader); aqui é população/ocupação.

Fonte: basedosdados.br_ibge_censo_2022.setor_censitario (pessoas, domicílios,
media_moradores_domicilios, geometria). Query ao vivo (≈2s, sempre fresco); cache em
processo por (município, lat, lng, raio).
"""
from __future__ import annotations

import logging
import math
import os
from typing import Any, Callable

logger = logging.getLogger(__name__)

_CACHE: dict[tuple, dict[str, Any] | None] = {}


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


def _agregar_supabase(lat: float, lng: float, raio_m: int, id_municipio: str | None) -> dict | None:
    """Espelho Supabase: bounding-box em lat/lng (indexado) + haversine preciso + agrega.

    Evita PostGIS — o box estreita pra ~poucas centenas de setores, daí filtro exato.
    """
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
           or os.environ.get("SUPABASE_KEY"))
    if not (os.environ.get("SUPABASE_URL") and key):
        return None
    raio_km = raio_m / 1000.0
    dlat = raio_km / 111.0
    dlng = raio_km / (111.0 * max(0.1, math.cos(math.radians(lat))))
    try:
        from tools.supabase_client import load_create_client

        sb = load_create_client()(os.environ["SUPABASE_URL"], key)
        q = (sb.table("censo_setor")
             .select("pessoas,domicilios,media_moradores,lat,lng")
             .gte("lat", lat - dlat).lte("lat", lat + dlat)
             .gte("lng", lng - dlng).lte("lng", lng + dlng))
        if id_municipio:
            q = q.eq("id_municipio", str(id_municipio))
        rows = getattr(q.limit(5000).execute(), "data", None) or []
    except Exception as exc:
        logger.warning("censo setor Supabase falhou: %s: %s", type(exc).__name__, exc)
        return None
    pop = dom = nset = 0
    for r in rows:
        rl, rg = r.get("lat"), r.get("lng")
        if rl is None or rg is None:
            continue
        if _haversine_km(lat, lng, rl, rg) <= raio_km:
            pop += int(r.get("pessoas") or 0)
            dom += int(r.get("domicilios") or 0)
            nset += 1
    if pop <= 0:
        return None
    return {"n_setores": nset, "populacao": pop, "domicilios": dom,
            "media_moradores": round(pop / dom, 2) if dom else 0.0}

_SQL = """
WITH alvo AS (SELECT ST_GEOGPOINT(@lng, @lat) AS pt)
SELECT
  COUNT(*) AS n_setores,
  SUM(pessoas) AS populacao,
  SUM(domicilios_particulares_ocupados) AS domicilios,
  ROUND(SUM(pessoas) / NULLIF(SUM(domicilios_particulares_ocupados), 0), 2) AS media_moradores
FROM `basedosdados.br_ibge_censo_2022.setor_censitario`, alvo
WHERE pessoas > 0
  {municipio_filter}
  AND ST_DWITHIN(geometria, alvo.pt, @raio_m)
"""


def _agregar_bq(lat: float, lng: float, raio_m: int, id_municipio: str | None) -> dict | None:
    """Fallback BQ live (ST_DWITHIN) quando o espelho Supabase não tem o município.

    Passa por basedosdados_loader.run_query → billing project + maximum_bytes_billed
    (5 GiB). Antes usava bigquery.Client() cru, sem teto: como roda POR RELATÓRIO e
    escaneia ~1.7 GiB (tabela nacional não particionada), um scan acidental sem cap
    faturava sem limite. O cap aborta antes de faturar, não silencioso.
    """
    try:
        from tools.basedosdados_loader import run_query

        mf = "AND id_municipio = @id_municipio" if id_municipio else ""
        params: dict[str, Any] = {
            "lat": float(lat),
            "lng": float(lng),
            "raio_m": float(raio_m),
        }
        if id_municipio:
            params["id_municipio"] = str(id_municipio)
        rows = run_query(_SQL.format(municipio_filter=mf), params=params)
        return rows[0] if rows else None
    except Exception as exc:
        logger.warning("censo setor BQ falhou (%s,%s): %s: %s", lat, lng, type(exc).__name__, exc)
        return None


def demografia_setor_censo(
    lat: float,
    lng: float,
    *,
    id_municipio: str | None = None,
    raio_m: int = 1500,
    _query_fn: Callable[..., dict | None] | None = None,
) -> dict[str, Any] | None:
    """Agrega o Censo 2022 (setores num raio do ponto) → pop/domicílios/ocupação reais.

    `id_municipio` (código IBGE 7 díg) filtra a execução (a tabela não é
    particionada — não reduz bytes faturados, só linhas processadas); opcional.
    `_query_fn` injetável para teste sem rede. Retorna None se BQ indisponível/sem dado.
    """
    if lat is None or lng is None:
        return None
    chave = (id_municipio or "", round(float(lat), 4), round(float(lng), 4), int(raio_m))
    if chave in _CACHE:
        return _CACHE[chave]

    if _query_fn is not None:
        row, fonte_dado = _query_fn(lat, lng, id_municipio, raio_m), "test"
    else:
        # 1. Espelho Supabase (rápido, offline). 2. BQ live (fallback / não espelhado).
        row = _agregar_supabase(lat, lng, raio_m, id_municipio)
        fonte_dado = "supabase_espelho"
        if row is None:
            row = _agregar_bq(lat, lng, raio_m, id_municipio)
            fonte_dado = "bigquery_live"

    if not row or not row.get("populacao"):
        _CACHE[chave] = None
        return None

    out = {
        "populacao": int(row["populacao"]),
        "domicilios": int(row.get("domicilios") or 0),
        "media_moradores": float(row.get("media_moradores") or 0.0),
        "n_setores": int(row.get("n_setores") or 0),
        "raio_m": int(raio_m),
        "fonte": "IBGE Censo 2022 por setor censitário (basedosdados)",
        "fonte_consulta": fonte_dado,  # supabase_espelho | bigquery_live | test
        "ano": 2022,
        "granularidade": "agregado de setores no raio do centróide do bairro",
    }
    _CACHE[chave] = out
    return out


def _bbox_from_ring(
    ring: list[tuple[float, float]],
    *,
    pad_deg: float = 0.003,
) -> tuple[float, float, float, float]:
    """(lat_min, lat_max, lng_min, lng_max) com padding pequeno."""
    lons = [float(p[0]) for p in ring]
    lats = [float(p[1]) for p in ring]
    return (
        min(lats) - pad_deg,
        max(lats) + pad_deg,
        min(lons) - pad_deg,
        max(lons) + pad_deg,
    )


def _carregar_setores_paged(
    table: str,
    select: str,
    id_municipio: str,
    *,
    ring: list[tuple[float, float]] | None = None,
    page_size: int = 1000,
    max_pages: int = 20,
) -> list[dict[str, Any]]:
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
           or os.environ.get("SUPABASE_KEY"))
    if not (os.environ.get("SUPABASE_URL") and key):
        return []
    try:
        from tools.supabase_client import load_create_client

        sb = load_create_client()(os.environ["SUPABASE_URL"], key)
        lat_min = lat_max = lng_min = lng_max = None
        if ring and len(ring) >= 3:
            lat_min, lat_max, lng_min, lng_max = _bbox_from_ring(ring)

        out: list[dict[str, Any]] = []
        for page in range(max_pages):
            start = page * page_size
            end = start + page_size - 1
            q = (sb.table(table)
                 .select(select)
                 .eq("id_municipio", str(id_municipio)))
            if lat_min is not None:
                q = (q.gte("lat", lat_min).lte("lat", lat_max)
                      .gte("lng", lng_min).lte("lng", lng_max))
            res = q.range(start, end).execute()
            chunk = list(getattr(res, "data", None) or [])
            out.extend(chunk)
            if len(chunk) < page_size:
                break
        return out
    except Exception as exc:
        logger.warning("carregar %s Supabase: %s: %s", table, type(exc).__name__, exc)
        return []


def carregar_setores_censo(
    id_municipio: str | None,
    *,
    ring: list[tuple[float, float]] | None = None,
    _rows: list[dict] | None = None,
    page_size: int = 1000,
    max_pages: int = 20,
) -> list[dict[str, Any]]:
    """Linhas `{lat, lng, pessoas, ...}` do espelho `censo_setor` (bbox+páginas)."""
    if _rows is not None:
        return [r for r in _rows if isinstance(r, dict)]
    if not id_municipio:
        return []
    return _carregar_setores_paged(
        "censo_setor",
        "pessoas,domicilios,media_moradores,lat,lng",
        str(id_municipio),
        ring=ring,
        page_size=page_size,
        max_pages=max_pages,
    )


_SELECT_IDADE_SEXO = (
    "lat,lng,pessoas,h_total,m_total,h_15_24,m_15_24,h_25_39,m_25_39,"
    "h_40_59,m_40_59,h_60_mais,m_60_mais"
)


def carregar_setores_idade_sexo(
    id_municipio: str | None,
    *,
    ring: list[tuple[float, float]] | None = None,
    _rows: list[dict] | None = None,
    page_size: int = 1000,
    max_pages: int = 20,
) -> list[dict[str, Any]]:
    """Espelho `censo_setor_idade_sexo` — bbox + páginas (pirâmide por setor)."""
    if _rows is not None:
        return [r for r in _rows if isinstance(r, dict)]
    if not id_municipio:
        return []
    return _carregar_setores_paged(
        "censo_setor_idade_sexo",
        _SELECT_IDADE_SEXO,
        str(id_municipio),
        ring=ring,
        page_size=page_size,
        max_pages=max_pages,
    )


def demografia_setor_poligono(
    id_municipio: str | None,
    ring: list[tuple[float, float]],
    *,
    _rows: list[dict] | None = None,
) -> dict[str, Any] | None:
    """Agrega setores cujo centróide cai dentro do polígono do bairro (Spec C)."""
    from tools.bairro_poligono import point_in_ring

    if not ring or len(ring) < 3:
        return None
    rows = _rows if _rows is not None else carregar_setores_censo(id_municipio, ring=ring)
    if not rows and _rows is None:
        if not id_municipio:
            return None
    acc = []
    for r in rows or []:
        rl, rg = r.get("lat"), r.get("lng")
        if rl is None or rg is None:
            continue
        if point_in_ring(float(rg), float(rl), ring):
            acc.append(r)
    if not acc:
        return None
    pop = sum(int(r.get("pessoas") or 0) for r in acc)
    dom = sum(int(r.get("domicilios") or 0) for r in acc)
    if pop <= 0:
        return None
    return {
        "populacao": pop,
        "domicilios": dom,
        "media_moradores": round(pop / dom, 2) if dom else 0.0,
        "n_setores": len(acc),
        "raio_m": None,
        "base": "poligono_ibge_bairro",
        "fonte": "IBGE Censo 2022 por setor · polígono IBGE bairro",
        "fonte_consulta": "test" if _rows is not None else "supabase_espelho",
        "ano": 2022,
        "granularidade": "agregado de setores no polígono IBGE do bairro",
    }
