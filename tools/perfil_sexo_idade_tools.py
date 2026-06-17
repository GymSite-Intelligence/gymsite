"""Perfil sexo×idade do público-alvo fitness por MUNICÍPIO (Censo 2022, BQ).

Gancho de marketing: % homens/mulheres na faixa fitness (default 25-40, exato via
`idade_anos` ano-a-ano da tabela populacao_idade_sexo). Granularidade município —
bairro exige polígono setor→bairro (ver tools/data/censo2022_vcodes_idade_sexo.json).

Determinístico, best-effort: sem código/erro/BQ → None (A2 degrada sem derrubar).
"""
from __future__ import annotations

from typing import Optional

from tools.parametros_metodologia import param

_BQ_TABELA = "basedosdados.br_ibge_censo_2022.populacao_idade_sexo"


def perfil_sexo_publico_fitness(id_municipio: str | int | None) -> Optional[dict]:
    """% homens/mulheres na faixa fitness (param publico_fitness_idade_min/max) p/
    o município (código IBGE 7 díg). None se sem código ou falha BQ."""
    if not id_municipio:
        return None
    cod = str(id_municipio).strip()
    if not cod.isdigit():
        return None

    idade_min = int(param("publico_fitness_idade_min"))
    idade_max = int(param("publico_fitness_idade_max"))

    try:
        from tools.basedosdados_loader import run_query

        q = f"""SELECT sexo, SUM(populacao) pop
FROM `{_BQ_TABELA}`
WHERE id_municipio = '{cod}' AND idade_anos BETWEEN {idade_min} AND {idade_max}
GROUP BY sexo"""
        rows = run_query(q)
    except Exception:
        return None

    d: dict[str, int] = {}
    for r in rows or []:
        sexo = (r.get("sexo") if isinstance(r, dict) else r[0]) or ""
        pop = r.get("pop") if isinstance(r, dict) else r[1]
        d[str(sexo).lower()] = int(pop or 0)

    homens = d.get("homens", 0)
    mulheres = d.get("mulheres", 0)
    total = homens + mulheres
    if total <= 0:
        return None

    pct_h = round(100 * homens / total, 1)
    pct_m = round(100 * mulheres / total, 1)
    maioria = "feminino" if mulheres > homens else "masculino" if homens > mulheres else "equilibrado"

    return {
        "id_municipio": cod,
        "faixa_idade": f"{idade_min}-{idade_max}",
        "homens": homens,
        "mulheres": mulheres,
        "total": total,
        "pct_homens": pct_h,
        "pct_mulheres": pct_m,
        "maioria": maioria,
        "fonte": "IBGE Censo 2022 (populacao_idade_sexo via BigQuery basedosdados)",
        "granularidade": "municipio",
    }


def insight_gancho_mkt(perfil: dict | None) -> str | None:
    """Linha de insight pro relatório a partir do perfil. None se sem dado."""
    if not perfil:
        return None
    f = perfil["faixa_idade"]
    pm = perfil["pct_mulheres"]
    ph = perfil["pct_homens"]
    lead = "mulheres" if pm >= ph else "homens"
    pct_lead = max(pm, ph)
    return (
        f"Público-alvo {f} anos no município: {pct_lead:.0f}% {lead} "
        f"({ph:.0f}% H / {pm:.0f}% M, Censo 2022) — gancho p/ tom e canais da campanha."
    )
