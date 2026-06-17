"""Espelha setor censitário → idade×sexo (Censo 2022) BQ → Supabase, NACIONAL.

Bloco 'Demografia' do agregado por setor (v01009–v01030, validado vs município -0,3%).
Roda OFFLINE (BQ); o extrator de bairro lê o espelho em prod (Cloud Run sem BQ-runtime),
agrega os setores do bairro (centróide + acumula até a pop-alvo) → pirâmide REAL do bairro,
sem o viés do rateio %município. Ver [[project_gymsite_censo_vcodes_idade_sexo]].

Faixas (v-code → segmento fitness): 15-24 = v01012+13 (H)/v01023+24 (M); 25-39 = v01014+15
/v01025+26; 40-59 = v01016+17/v01027+28; 60+ = v01018+19/v01029+30. Total: v00011/v00014.
Uso:  python -m tools.censo_setor_idade_sexo_loader
"""
from __future__ import annotations


def popular(limite_municipio: str | None = None) -> int:
    from tools.basedosdados_loader import run_query
    from db.supabase_writer import _get_client

    filtro = f"AND id_municipio = '{limite_municipio}'" if limite_municipio else ""
    q = f"""SELECT id_setor_censitario id, id_municipio,
  ST_Y(ST_CENTROID(geometria)) lat, ST_X(ST_CENTROID(geometria)) lng,
  v00005 pessoas, v00011 h_total, v00014 m_total,
  (v01012+v01013) h_15_24, (v01023+v01024) m_15_24,
  (v01014+v01015) h_25_39, (v01025+v01026) m_25_39,
  (v01016+v01017) h_40_59, (v01027+v01028) m_40_59,
  (v01018+v01019) h_60_mais, (v01029+v01030) m_60_mais
FROM `basedosdados.br_ibge_censo_2022.setor_censitario`
WHERE v00005 > 0 {filtro}"""
    rows = run_query(q)

    cols = ["pessoas", "h_total", "m_total", "h_15_24", "m_15_24", "h_25_39", "m_25_39",
            "h_40_59", "m_40_59", "h_60_mais", "m_60_mais"]
    recs = []
    for r in rows or []:
        rec = {"id_setor": r["id"], "id_municipio": r["id_municipio"],
               "lat": r.get("lat"), "lng": r.get("lng")}
        for c in cols:
            try:
                rec[c] = int(r.get(c) or 0)
            except (TypeError, ValueError):
                rec[c] = 0
        recs.append(rec)

    sb = _get_client()
    if sb is None:
        raise RuntimeError("Supabase client indisponível")
    for i in range(0, len(recs), 1000):
        sb.table("censo_setor_idade_sexo").upsert(recs[i:i + 1000], on_conflict="id_setor").execute()
    return len(recs)


if __name__ == "__main__":
    import sys

    from dotenv import load_dotenv

    load_dotenv()
    mun = sys.argv[1] if len(sys.argv) > 1 else None
    n = popular(mun)
    print(f"OK: {n} setores espelhados em censo_setor_idade_sexo" + (f" (mun {mun})" if mun else " (nacional)"))
