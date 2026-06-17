"""Espelha município → split sexo×idade (Censo 2022) BQ → Supabase, TODAS as faixas.

Roda OFFLINE (com acesso BigQuery); a tool perfil_sexo_publico_fitness lê o espelho em
prod (Cloud Run não tem BQ-runtime). Popula:
  - faixas GRANULARES de 5 anos (0-4 … 100+) p/ flexibilidade total;
  - segmentos FITNESS ancorados no benchmark (jovem/core/maduro/silver/público/gancho).
Tabela: municipio_publico_sexo PK (id_municipio, faixa_idade).
Uso:  python -m tools.municipio_publico_sexo_loader
"""
from __future__ import annotations

# (label, idade_min, idade_max) inclusivo. idade_anos é ano-a-ano → faixa EXATA.
_FAIXAS_GRANULARES = [(f"{a}-{a+4}", a, a + 4) for a in range(0, 100, 5)] + [("100+", 100, 130)]
# Segmentos fitness (benchmark ACAD/IHRSA + definição GymSite 18-45):
_FAIXAS_FITNESS = [
    ("15-24", 15, 24),   # jovem / estudante / iniciante
    ("25-39", 25, 39),   # core profissional (pico de membership)
    ("40-59", 40, 59),   # maduro / saúde-manutenção
    ("60+", 60, 130),    # silver / terceira idade
    ("18-45", 18, 45),   # público fitness amplo (definição do projeto)
    ("25-40", 25, 40),   # gancho atual (publico_fitness_idade_min/max)
]
_FAIXAS = _FAIXAS_GRANULARES + _FAIXAS_FITNESS


def popular() -> int:
    from tools.basedosdados_loader import run_query
    from db.supabase_writer import _get_client

    q = """SELECT id_municipio, idade_anos, sexo, SUM(populacao) pop
FROM `basedosdados.br_ibge_censo_2022.populacao_idade_sexo`
GROUP BY id_municipio, idade_anos, sexo"""
    rows = run_query(q)

    # mun -> {idade: {homens, mulheres}}
    por_mun: dict[str, dict[int, dict[str, int]]] = {}
    for r in rows or []:
        m = r["id_municipio"]
        try:
            idade = int(r["idade_anos"])
        except (TypeError, ValueError):
            continue
        s = (r["sexo"] or "").lower()
        p = int(r["pop"] or 0)
        d = por_mun.setdefault(m, {}).setdefault(idade, {"homens": 0, "mulheres": 0})
        if "home" in s:
            d["homens"] += p
        elif "mulh" in s:
            d["mulheres"] += p

    recs = []
    for m, idades in por_mun.items():
        for label, lo, hi in _FAIXAS:
            h = sum(v["homens"] for a, v in idades.items() if lo <= a <= hi)
            mu = sum(v["mulheres"] for a, v in idades.items() if lo <= a <= hi)
            t = h + mu
            if t <= 0:
                continue
            recs.append({
                "id_municipio": m, "faixa_idade": label, "homens": h, "mulheres": mu, "total": t,
                "pct_homens": round(100 * h / t, 1), "pct_mulheres": round(100 * mu / t, 1),
            })

    sb = _get_client()
    if sb is None:
        raise RuntimeError("Supabase client indisponível (SUPABASE_URL/SERVICE_ROLE_KEY)")
    for i in range(0, len(recs), 1000):
        sb.table("municipio_publico_sexo").upsert(
            recs[i:i + 1000], on_conflict="id_municipio,faixa_idade"
        ).execute()
    return len(recs)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    n = popular()
    print(f"OK: {n} linhas (municipio×faixa) espelhadas em municipio_publico_sexo")
