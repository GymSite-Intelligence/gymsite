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


_SEGMENTOS_BAIRRO = (
    ("15-24", "h_15_24", "m_15_24"),
    ("25-39", "h_25_39", "m_25_39"),
    ("40-59", "h_40_59", "m_40_59"),
    ("60+", "h_60_mais", "m_60_mais"),
)


def perfil_sexo_idade_bairro(
    id_municipio: str | int | None, lat_centro: float | None, lng_centro: float | None,
    pop_alvo: float | None,
) -> Optional[dict]:
    """Pirâmide REAL idade×sexo do BAIRRO (Censo 2022 por setor) — sem o viés do rateio
    %município. Agrega os setores mais próximos do centróide até somar ~pop_alvo (pop do
    bairro, IPECE/Censo). Lê o espelho Supabase censo_setor_idade_sexo (prod-safe, sem BQ).
    None se faltar input ou cobertura."""
    import math

    if not id_municipio or lat_centro is None or lng_centro is None or not pop_alvo:
        return None
    cod = str(id_municipio).strip()
    if not cod.isdigit():
        return None
    try:
        from db.supabase_writer import _get_client

        sb = _get_client()
        if sb is None:
            return None
        res = (
            sb.table("censo_setor_idade_sexo")
            .select("lat,lng,pessoas,h_total,m_total,h_15_24,m_15_24,h_25_39,m_25_39,"
                    "h_40_59,m_40_59,h_60_mais,m_60_mais")
            .eq("id_municipio", cod)
            .execute()
        )
        setores = [s for s in (res.data or []) if s.get("lat") is not None and s.get("pessoas")]
        if not setores:
            return None
    except Exception:
        return None

    clat, clng = float(lat_centro), float(lng_centro)
    coslat = math.cos(math.radians(clat))

    def _dist(s: dict) -> float:
        return math.hypot((float(s["lat"]) - clat) * 111.0, (float(s["lng"]) - clng) * 111.0 * coslat)

    setores.sort(key=_dist)
    acc: list[dict] = []
    pop = 0
    for s in setores:
        acc.append(s)
        pop += int(s.get("pessoas") or 0)
        if pop >= pop_alvo:
            break
    if not acc:
        return None

    def _soma(c: str) -> int:
        return sum(int(s.get(c) or 0) for s in acc)

    segmentos = {}
    for label, hc, mc in _SEGMENTOS_BAIRRO:
        h, m = _soma(hc), _soma(mc)
        t = h + m
        if t <= 0:
            continue
        segmentos[label] = {
            "homens": h, "mulheres": m, "total": t,
            "pct_homens": round(100 * h / t, 1), "pct_mulheres": round(100 * m / t, 1),
        }
    h_tot, m_tot = _soma("h_total"), _soma("m_total")
    tot = h_tot + m_tot
    if tot <= 0:
        return None
    # Faixa-alvo do gancho (25-39 ≈ 25-40; v-code não separa o ano 40).
    alvo = segmentos.get("25-39") or {}
    return {
        "id_municipio": cod,
        "granularidade": "bairro (setor censitário real)",
        "n_setores": len(acc),
        "pop_agregada": pop,
        "pop_alvo": int(pop_alvo),
        "faixa_idade": "25-39",
        "homens": alvo.get("homens"),
        "mulheres": alvo.get("mulheres"),
        "total": alvo.get("total"),
        "pct_homens": alvo.get("pct_homens"),
        "pct_mulheres": alvo.get("pct_mulheres"),
        "maioria": ("feminino" if (alvo.get("pct_mulheres") or 0) > (alvo.get("pct_homens") or 0)
                    else "masculino"),
        "segmentos": segmentos,
        "sexo_total": {"homens": h_tot, "mulheres": m_tot,
                       "pct_homens": round(100 * h_tot / tot, 1),
                       "pct_mulheres": round(100 * m_tot / tot, 1)},
        "fonte": "IBGE Censo 2022 — agregado por setor censitário (Demografia v01009–v01030)",
    }


def _perfil_do_espelho_supabase(cod: str, faixa: str) -> Optional[dict]:
    """Lê o split sexo×idade do espelho Supabase municipio_publico_sexo (mirror do BQ,
    populado offline) p/ a FAIXA pedida. Funciona em prod (Supabase) sem BQ-runtime.
    A tabela tem PK (id_municipio, faixa_idade) — filtrar pela faixa é obrigatório."""
    try:
        from db.supabase_writer import _get_client

        sb = _get_client()
        if sb is None:
            return None
        res = (
            sb.table("municipio_publico_sexo")
            .select("faixa_idade,homens,mulheres,total,pct_homens,pct_mulheres,fonte")
            .eq("id_municipio", cod)
            .eq("faixa_idade", faixa)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return None
        r = rows[0]
        h, m = int(r["homens"]), int(r["mulheres"])
        return {
            "id_municipio": cod,
            "faixa_idade": r.get("faixa_idade") or "25-40",
            "homens": h,
            "mulheres": m,
            "total": int(r.get("total") or (h + m)),
            "pct_homens": float(r["pct_homens"]),
            "pct_mulheres": float(r["pct_mulheres"]),
            "maioria": "feminino" if m > h else "masculino" if h > m else "equilibrado",
            "fonte": r.get("fonte") or "IBGE Censo 2022 (espelho Supabase)",
            "granularidade": "municipio",
        }
    except Exception:
        return None


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

    # PRIMÁRIO: espelho Supabase municipio_publico_sexo (funciona em prod; BQ-runtime
    # falha no Cloud Run por falta de acesso BigQuery — por isso esta tool dava None).
    pre = _perfil_do_espelho_supabase(cod, f"{idade_min}-{idade_max}")
    if pre is not None:
        return pre

    homens = mulheres = 0
    try:
        from tools.basedosdados_loader import run_query

        q = f"""SELECT sexo, SUM(populacao) pop
FROM `{_BQ_TABELA}`
WHERE id_municipio = '{cod}' AND idade_anos BETWEEN {idade_min} AND {idade_max}
GROUP BY sexo"""
        rows = run_query(q)
        d: dict[str, int] = {}
        for r in rows or []:
            sexo = (r.get("sexo") if isinstance(r, dict) else r[0]) or ""
            pop = r.get("pop") if isinstance(r, dict) else r[1]
            d[str(sexo).lower()] = int(pop or 0)
        homens = d.get("homens", 0)
        mulheres = d.get("mulheres", 0)
    except Exception as e:  # noqa: BLE001
        print(f"[perfil_sexo_publico_fitness] BQ fallback falhou p/ id={cod}: {type(e).__name__}: {e}")
        return None

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
