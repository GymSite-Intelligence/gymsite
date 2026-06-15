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


def _bq_client():
    from google.cloud import bigquery

    return bigquery.Client()


def _agregar_bq(lat: float, lng: float, raio_m: int, id_municipio: str | None) -> dict | None:
    """Fallback BQ live (ST_DWITHIN) quando o espelho Supabase não tem o município."""
    try:
        from google.cloud import bigquery

        cli = _bq_client()
        mf = "AND id_municipio = @id_municipio" if id_municipio else ""
        params = [
            bigquery.ScalarQueryParameter("lat", "FLOAT64", float(lat)),
            bigquery.ScalarQueryParameter("lng", "FLOAT64", float(lng)),
            bigquery.ScalarQueryParameter("raio_m", "FLOAT64", float(raio_m)),
        ]
        if id_municipio:
            params.append(bigquery.ScalarQueryParameter("id_municipio", "STRING", str(id_municipio)))
        job = cli.query(
            _SQL.format(municipio_filter=mf),
            job_config=bigquery.QueryJobConfig(query_parameters=params),
        )
        r = next(iter(job.result()), None)
        return dict(r.items()) if r is not None else None
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

    `id_municipio` (código IBGE 7 díg) acelera a query (partição); opcional.
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
