"""Espelha município → split sexo×idade do público fitness (Censo 2022) BQ → Supabase.

Roda OFFLINE (onde há acesso BigQuery); a tool perfil_sexo_publico_fitness lê o espelho
em prod (Cloud Run não tem BQ-runtime). Re-rodar se a faixa (publico_fitness_idade_*)
mudar. Uso:  python -m tools.municipio_publico_sexo_loader
"""
from __future__ import annotations


def popular() -> int:
    from tools.basedosdados_loader import run_query
    from tools.parametros_metodologia import param
    from db.supabase_writer import _get_client

    lo, hi = int(param("publico_fitness_idade_min")), int(param("publico_fitness_idade_max"))
    q = f"""SELECT id_municipio, sexo, SUM(populacao) pop
FROM `basedosdados.br_ibge_censo_2022.populacao_idade_sexo`
WHERE idade_anos BETWEEN {lo} AND {hi}
GROUP BY id_municipio, sexo"""
    rows = run_query(q)

    agg: dict[str, dict[str, int]] = {}
    for r in rows or []:
        m = r["id_municipio"]
        s = (r["sexo"] or "").lower()
        p = int(r["pop"] or 0)
        agg.setdefault(m, {"homens": 0, "mulheres": 0})
        if "home" in s:
            agg[m]["homens"] += p
        elif "mulh" in s:
            agg[m]["mulheres"] += p

    faixa = f"{lo}-{hi}"
    recs = []
    for m, d in agg.items():
        h, mu = d["homens"], d["mulheres"]
        t = h + mu
        if t <= 0:
            continue
        recs.append({
            "id_municipio": m, "faixa_idade": faixa, "homens": h, "mulheres": mu, "total": t,
            "pct_homens": round(100 * h / t, 1), "pct_mulheres": round(100 * mu / t, 1),
        })

    sb = _get_client()
    if sb is None:
        raise RuntimeError("Supabase client indisponível (SUPABASE_URL/SERVICE_ROLE_KEY)")
    for i in range(0, len(recs), 500):
        sb.table("municipio_publico_sexo").upsert(recs[i:i + 500], on_conflict="id_municipio").execute()
    return len(recs)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    n = popular()
    print(f"OK: {n} municípios espelhados em municipio_publico_sexo")
