"""
Loader genérico para tabelas públicas do basedosdados (BigQuery).

Rota canônica das fontes nacionais padronizadas (CNO, Censo, RAIS, CAGED…).
Ver docs/arquitetura/COMPILADO_FONTES_DADOS.md §7.

Custo: free tier 1 TiB/mês. Guarda obrigatória `maximum_bytes_billed` (default 5 GiB)
aborta scans acidentais antes de faturar. Sempre filtrar por sigla_uf/id_municipio.

Auth: ADC. Em prod/CI, GOOGLE_APPLICATION_CREDENTIALS (service account com
roles/bigquery.jobUser). Local: gcloud auth.
"""
from __future__ import annotations

import os
from typing import Any

# Projeto de BILLING das queries (datasets BD são públicos; faturamento é nosso).
BILLING_PROJECT = (
    os.environ.get("BQ_BILLING_PROJECT")
    or os.environ.get("GOOGLE_CLOUD_PROJECT")
    or "gen-lang-client-0106729343"
)

# Cap de custo por query. 5 GiB << 1 TiB free; aborta erro antes de faturar.
DEFAULT_MAX_BYTES_BILLED = int(os.environ.get("BQ_MAX_BYTES_BILLED", 5 * 1024**3))


def _client():
    from google.cloud import bigquery

    return bigquery.Client(project=BILLING_PROJECT)


def run_query(
    sql: str,
    *,
    params: dict[str, Any] | None = None,
    max_bytes_billed: int = DEFAULT_MAX_BYTES_BILLED,
) -> list[dict[str, Any]]:
    """Roda query BQ com guarda de custo; retorna lista de dicts.

    params: nomeados (@nome) → BigQuery ScalarQueryParameter (str/int/float/bool).
    Levanta se exceder max_bytes_billed (proteção de custo), não silencioso.
    """
    from google.cloud import bigquery

    qp: list[Any] = []
    for k, v in (params or {}).items():
        if isinstance(v, bool):
            t = "BOOL"
        elif isinstance(v, int):
            t = "INT64"
        elif isinstance(v, float):
            t = "FLOAT64"
        else:
            t = "STRING"
            v = str(v)
        qp.append(bigquery.ScalarQueryParameter(k, t, v))

    job_config = bigquery.QueryJobConfig(
        query_parameters=qp,
        maximum_bytes_billed=max_bytes_billed,
        use_legacy_sql=False,
    )
    job = _client().query(sql, job_config=job_config)
    return [dict(row.items()) for row in job.result()]


def estimar_bytes(sql: str, *, params: dict[str, Any] | None = None) -> int:
    """Dry-run: bytes que a query escanearia (para checagem de custo)."""
    from google.cloud import bigquery

    qp: list[Any] = []
    for k, v in (params or {}).items():
        t = "STRING"
        qp.append(bigquery.ScalarQueryParameter(k, t, str(v)))
    cfg = bigquery.QueryJobConfig(
        query_parameters=qp, dry_run=True, use_query_cache=False, use_legacy_sql=False
    )
    job = _client().query(sql, job_config=cfg)
    return int(job.total_bytes_processed or 0)
