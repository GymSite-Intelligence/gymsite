"""
Espelha o IBGE Censo 2022 por setor censitário (BigQuery basedosdados) → Supabase.

Persiste centróide (lat/lng) + pessoas/domicílios/média_moradores por setor — SEM
geometria (leve). A query por raio no Supabase usa bounding-box em lat/lng + haversine
(ver censo_setor_tools). Renda 2022 por setor NÃO existe (IBGE não liberou) → renda
vem do CKAN (bairro_renda_loader).

Uso:
  python -m tools.censo_setor_loader --municipio 2304400   # um município (IBGE 7 díg)
  python -m tools.censo_setor_loader --nacional            # ~459k setores (pessoas>0)
"""
from __future__ import annotations

import argparse
import os

_BQ_SQL = """
SELECT
  id_setor_censitario AS id_setor,
  id_municipio,
  CAST(pessoas AS INT64) AS pessoas,
  CAST(domicilios_particulares_ocupados AS INT64) AS domicilios,
  ROUND(media_moradores_domicilios, 2) AS media_moradores,
  ROUND(ST_Y(ST_CENTROID(geometria)), 6) AS lat,
  ROUND(ST_X(ST_CENTROID(geometria)), 6) AS lng
FROM `basedosdados.br_ibge_censo_2022.setor_censitario`
WHERE pessoas > 0 {municipio_filter}
"""


def _supabase():
    from tools.supabase_client import load_create_client

    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY"))
    return load_create_client()(os.environ["SUPABASE_URL"], key)


def carregar(*, id_municipio: str | None = None, batch: int = 2000) -> int:
    """Lê o Censo do BQ e faz upsert no Supabase. Retorna nº de setores carregados."""
    from google.cloud import bigquery

    cli = bigquery.Client()
    mf = f"AND id_municipio = '{id_municipio}'" if id_municipio else ""
    rows = list(cli.query(_BQ_SQL.format(municipio_filter=mf)).result())
    print(f"BQ retornou {len(rows)} setores{' (município ' + id_municipio + ')' if id_municipio else ' (nacional)'}")

    sb = _supabase()
    total = 0
    lote: list[dict] = []
    for r in rows:
        lote.append({
            "id_setor": r["id_setor"], "id_municipio": r["id_municipio"],
            "pessoas": r["pessoas"], "domicilios": r["domicilios"],
            "media_moradores": float(r["media_moradores"]) if r["media_moradores"] is not None else None,
            "lat": r["lat"], "lng": r["lng"], "ano": 2022,
        })
        if len(lote) >= batch:
            sb.table("censo_setor").upsert(lote, on_conflict="id_setor").execute()
            total += len(lote)
            print(f"  upsert {total}/{len(rows)}")
            lote = []
    if lote:
        sb.table("censo_setor").upsert(lote, on_conflict="id_setor").execute()
        total += len(lote)
    print(f"OK: {total} setores no Supabase")
    return total


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--municipio", help="código IBGE 7 dígitos")
    g.add_argument("--nacional", action="store_true")
    a = p.parse_args()
    carregar(id_municipio=None if a.nacional else a.municipio)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
