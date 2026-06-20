"""Loader one-time do espelho municipio_pib (PIB + população por município).

Fonte: BigQuery basedosdados (br_ibge_pib + br_ibge_populacao) — 1 query, confiável
(IBGE REST dava timeout no bulk). Determinístico → espelhado no Supabase, lido em
runtime pelo MRLR (aluguel/m²). Roda anual. Mesmo padrão de renda_bairro/censo_setor.
"""
from __future__ import annotations

import os
from tools.db_schema import tbl

_QUERY = """
WITH pib AS (
  SELECT id_municipio, pib, ano FROM `basedosdados.br_ibge_pib.municipio`
  WHERE ano = (SELECT MAX(ano) FROM `basedosdados.br_ibge_pib.municipio`)
),
pop AS (
  SELECT id_municipio, populacao FROM `basedosdados.br_ibge_populacao.municipio`
  WHERE ano = (SELECT MAX(ano) FROM `basedosdados.br_ibge_populacao.municipio`)
)
SELECT p.id_municipio, p.pib, p.ano, o.populacao
FROM pib p LEFT JOIN pop o USING(id_municipio)
WHERE o.populacao > 0
"""


def carregar() -> dict:
    from google.cloud import bigquery

    bq = bigquery.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0106729343"))
    rows_bq = list(bq.query(_QUERY).result())

    from tools.supabase_client import load_create_client

    cli = load_create_client()(os.environ["SUPABASE_URL"],
                               os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    rows = []
    ano = None
    for r in rows_bq:
        pib = float(r["pib"]) if r["pib"] is not None else None
        pop = int(r["populacao"]) if r["populacao"] else None
        ano = int(r["ano"]) if r["ano"] else ano
        if not (pib and pop):
            continue
        rows.append({
            "id_municipio": str(r["id_municipio"]),
            "populacao": pop,
            "pib_reais": pib,
            "pib_per_capita": round(pib / pop, 2),
            "ano": ano,
            "fonte": "BigQuery basedosdados (br_ibge_pib + br_ibge_populacao)",
        })
    n = 0
    for i in range(0, len(rows), 500):
        tbl(cli, "municipio_pib").upsert(rows[i:i + 500], on_conflict="id_municipio").execute()
        n += len(rows[i:i + 500])
    return {"municipios": n, "ano": ano}


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    print(carregar())
