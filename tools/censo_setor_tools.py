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
from typing import Any, Callable

logger = logging.getLogger(__name__)

_CACHE: dict[tuple, dict[str, Any] | None] = {}

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
        row = _query_fn(lat, lng, id_municipio, raio_m)
    else:
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
            row = dict(r.items()) if r is not None else None
        except Exception as exc:
            logger.warning("censo setor BQ falhou (%s,%s): %s: %s", lat, lng, type(exc).__name__, exc)
            _CACHE[chave] = None
            return None

    if not row or not row.get("populacao"):
        _CACHE[chave] = None
        return None

    out = {
        "populacao": int(row["populacao"]),
        "domicilios": int(row.get("domicilios") or 0),
        "media_moradores": float(row.get("media_moradores") or 0.0),
        "n_setores": int(row.get("n_setores") or 0),
        "raio_m": int(raio_m),
        "fonte": "IBGE Censo 2022 por setor censitário (BigQuery basedosdados)",
        "ano": 2022,
        "granularidade": "agregado de setores no raio do centróide do bairro",
    }
    _CACHE[chave] = out
    return out
