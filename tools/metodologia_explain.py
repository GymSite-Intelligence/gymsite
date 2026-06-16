"""
Granularização da metodologia — decompõe os scores do veredito em camadas
auditáveis, cada folha rastreada à sua fonte (param Supabase parametros_metodologia).

Árvore determinística (SEM LLM):

    veredito           = cutoffs param 8/6/4 sobre score_decisao
    score_decisao      = score_top1_candidato OU score_bairro (fallback)
    score_bairro       = média(score_demografico, score_concorrencia, score_viabilidade)
    score_top1         = média(geoscout_top1, demografico, concorrencia, viabilidade)
      ├ score_demografico   = pop_faixa(cutoffs) + renda(cutoffs) + base   [ibge_tools]
      ├ score_concorrencia  = bonus(saturação) − penalidades(qtd, rating)  [competitor_tools]
      ├ score_viabilidade   = payback(cutoffs) + ocupação(cutoffs) + base  [financial_tools]
      └ geoscout_top1       = âncora geradora (distâncias param)            [anchoring_tools]

Cada `_leaf` carrega {param, valor, categoria, fonte} de param_meta → transparência total.
Reutilizável pela página /metodologia e por auditoria. Folhas demográficas usam dado
real (Censo/CKAN); concorrência/viabilidade recebem os inputs do pipeline (A3/A4).
"""
from __future__ import annotations

from typing import Any

from tools.parametros_metodologia import param, param_meta


def _leaf(nome: str, *, usado: bool = True) -> dict[str, Any]:
    """Folha auditável: valor + categoria + fonte do parâmetro."""
    m = param_meta(nome)
    return {"param": nome, "valor": m["valor"], "categoria": m.get("categoria"),
            "fonte": m.get("fonte"), "usado": usado}


# ── score_demografico (A2 / ibge_tools) ──────────────────────────────────────
def explicar_score_demografico(pop_faixa: float, renda_media: float) -> dict[str, Any]:
    pts_pop, pop_param = 0.0, None
    for nome, pts in (("score_demo_pop_alta", 4.0), ("score_demo_pop_media", 3.0),
                      ("score_demo_pop_baixa", 2.0), ("score_demo_pop_minima", 1.0)):
        if pop_faixa >= param(nome):
            pts_pop, pop_param = pts, nome
            break
    pts_renda, renda_param = 0.0, None
    for nome, pts in (("score_demo_renda_alta", 4.0), ("score_demo_renda_media", 3.0),
                      ("score_demo_renda_baixa", 2.0), ("score_demo_renda_minima", 1.0)):
        if renda_media >= param(nome):
            pts_renda, renda_param = pts, nome
            break
    base = param("score_demo_base")
    score = min(pts_pop + pts_renda + base, 10.0)
    return {
        "score": round(score, 2),
        "formula": "min(pts_pop + pts_renda + base, 10)",
        "componentes": {
            "pop_faixa": {"valor": pop_faixa, "pts": pts_pop,
                          "cutoff": _leaf(pop_param) if pop_param else "abaixo do mínimo"},
            "renda_media": {"valor": renda_media, "pts": pts_renda,
                            "cutoff": _leaf(renda_param) if renda_param else "abaixo do mínimo"},
            "base": _leaf("score_demo_base"),
        },
    }


def explicar_demografico(cidade: str, uf: str, faixa: str = "18-45",
                         bairro: str | None = None) -> dict[str, Any]:
    """A2 determinístico real (IBGE/Censo) + decomposição sourced do score."""
    from tools.ibge_tools import analise_demografica_completa

    a2 = analise_demografica_completa(cidade, uf, faixa, bairro=bairro)
    pop_faixa = a2.get("populacao_faixa_18_45") or 0
    renda = a2.get("renda_media_domiciliar") or 0.0
    return {
        "fonte_dados": {
            "populacao": a2.get("fonte_populacao", "IBGE"),
            "renda": a2.get("fonte_renda") or a2.get("renda_uf_fonte"),
            "faixa_pct": _leaf(f"faixa_pct_{faixa.replace('-', '_')}", usado=True)
                         if f"faixa_pct_{faixa.replace('-', '_')}" in _PARAM_FAIXAS else _leaf("faixa_pct_default"),
            "publico_potencial_taxa": _leaf("penetracao_potencial_fitness"),
        },
        "populacao_total": a2.get("populacao_total"),
        "populacao_faixa": pop_faixa,
        "publico_potencial": a2.get("publico_potencial_fitness"),
        "renda_media": renda,
        "score_demografico": explicar_score_demografico(pop_faixa, renda),
        "classificacao": a2.get("classificacao"),
    }


_PARAM_FAIXAS = {"faixa_pct_15_29", "faixa_pct_18_35", "faixa_pct_18_45",
                 "faixa_pct_20_40", "faixa_pct_25_50"}


# ── score_concorrencia (A3 / competitor_tools) ───────────────────────────────
def explicar_score_concorrencia(num_concorrentes: int, rating_medio: float,
                                raio_km: float = 3.0) -> dict[str, Any]:
    import math

    from tools.competitor_tools import classificar_saturacao

    area = math.pi * raio_km ** 2
    densidade = num_concorrentes / area if area > 0 else 0
    saturacao = classificar_saturacao(num_concorrentes, raio_km)
    bonus_param = {"BAIXO": "score_conc_bonus_baixo", "MEDIO": "score_conc_bonus_medio",
                   "ALTO": "score_conc_bonus_alto", "SATURADO": "score_conc_bonus_saturado"}[saturacao]
    bonus = param(bonus_param)
    pen_qtd = min(num_concorrentes * param("score_conc_penalidade_por_conc"),
                  param("score_conc_penalidade_teto"))
    pen_rating = ((rating_medio / 5.0) * param("score_conc_rating_mult")
                  if rating_medio else param("score_conc_rating_default"))
    score = max(0.0, min(10.0, bonus + (10 - pen_qtd * 2) / 10 - pen_rating))
    return {
        "score": round(score, 2),
        "formula": "bonus(saturação) + (10 − pen_qtd·2)/10 − pen_rating",
        "saturacao": saturacao,
        "densidade_km2": round(densidade, 2),
        "componentes": {
            "densidade_cutoffs": [_leaf("saturacao_densidade_baixo"),
                                  _leaf("saturacao_densidade_medio"),
                                  _leaf("saturacao_densidade_alto")],
            "bonus_saturacao": _leaf(bonus_param),
            "penalidade_qtd": {"valor": round(pen_qtd, 2),
                               "fator": _leaf("score_conc_penalidade_por_conc"),
                               "teto": _leaf("score_conc_penalidade_teto")},
            "penalidade_rating": {"valor": round(pen_rating, 2),
                                  "mult": _leaf("score_conc_rating_mult")},
        },
    }


# ── score_viabilidade (A4 / financial_tools) ─────────────────────────────────
def explicar_score_viabilidade(payback_meses: float, ocupacao_break: float) -> dict[str, Any]:
    pts_pb, pb_param = 0.0, None
    for nome, pts in (("payback_limiar_excelente", 4.0), ("payback_limiar_bom", 3.0),
                      ("payback_limiar_regular", 2.0), ("payback_limiar_fraco", 1.0)):
        if payback_meses <= param(nome):
            pts_pb, pb_param = pts, nome
            break
    pts_oc, oc_param = 0.0, None
    for nome, pts in (("ocupacao_break_otima", 3.0), ("ocupacao_break_boa", 2.0),
                      ("ocupacao_break_limite", 1.0)):
        if ocupacao_break < param(nome):
            pts_oc, oc_param = pts, nome
            break
    # scorer canônico (mesma fonte que o A4 usa em produção)
    from tools.financial_tools import calcular_score_viabilidade
    score = calcular_score_viabilidade(payback_meses, ocupacao_break)
    return {
        "score": round(score, 2),
        "formula": "min(pts_payback + pts_ocupacao + score_viab_base, 10)",
        "componentes": {
            "payback_meses": {"valor": payback_meses, "pts": pts_pb,
                              "cutoff": _leaf(pb_param) if pb_param else "acima do limite"},
            "ocupacao_break": {"valor": ocupacao_break, "pts": pts_oc,
                               "cutoff": _leaf(oc_param) if oc_param else "acima do limite"},
        },
    }


# ── score_bairro + veredito (A6) ─────────────────────────────────────────────
def explicar_veredito(score_decisao: float) -> dict[str, Any]:
    if score_decisao >= param("veredito_limiar_aprovado"):
        v, p = "APROVADO", "veredito_limiar_aprovado"
    elif score_decisao >= param("veredito_limiar_ressalvas"):
        v, p = "APROVADO COM RESSALVAS", "veredito_limiar_ressalvas"
    elif score_decisao >= param("veredito_limiar_investigar"):
        v, p = "INVESTIGAR MAIS", "veredito_limiar_investigar"
    else:
        v, p = "REPROVADO", None
    return {"veredito": v, "score_decisao": round(score_decisao, 2),
            "cutoff_disparado": _leaf(p) if p else "abaixo de todos os cutoffs",
            "cutoffs": [_leaf("veredito_limiar_aprovado"), _leaf("veredito_limiar_ressalvas"),
                        _leaf("veredito_limiar_investigar")]}


def explicar_score_bairro(score_demografico: float | None, score_concorrencia: float | None,
                          score_viabilidade: float | None,
                          geoscout_top1: float | None = None) -> dict[str, Any]:
    dims = [s for s in (score_demografico, score_concorrencia, score_viabilidade) if s is not None]
    score_bairro = round(sum(dims) / len(dims), 2) if dims else None
    top1_dims = [s for s in (geoscout_top1, score_demografico, score_concorrencia, score_viabilidade)
                 if s is not None]
    score_top1 = round(sum(top1_dims) / len(top1_dims), 2) if top1_dims else None
    score_decisao = score_top1 if score_top1 is not None else score_bairro
    return {
        "score_bairro": score_bairro,
        "score_top1_candidato": score_top1,
        "score_decisao": score_decisao,
        "formula_bairro": "média(demografico, concorrencia, viabilidade)",
        "formula_top1": "média(geoscout_top1, demografico, concorrencia, viabilidade)",
        "dimensoes": {"demografico": score_demografico, "concorrencia": score_concorrencia,
                      "viabilidade": score_viabilidade, "geoscout_top1": geoscout_top1},
        "veredito": explicar_veredito(score_decisao) if score_decisao is not None else None,
    }


def explicar_metodologia(
    cidade: str, uf: str, *, bairro: str | None = None, faixa: str = "18-45",
    # inputs do pipeline (A3/A4) — em produção vêm de Places/financeiro real:
    num_concorrentes: int, rating_medio: float, raio_km: float = 3.0,
    payback_meses: float, ocupacao_break: float, geoscout_top1: float | None = None,
) -> dict[str, Any]:
    """Árvore completa do veredito, granular e sourced (determinístico, sem LLM)."""
    demo = explicar_demografico(cidade, uf, faixa, bairro=bairro)
    conc = explicar_score_concorrencia(num_concorrentes, rating_medio, raio_km)
    viab = explicar_score_viabilidade(payback_meses, ocupacao_break)
    bairro_veredito = explicar_score_bairro(
        demo["score_demografico"]["score"], conc["score"], viab["score"], geoscout_top1)
    return {"cidade": cidade, "uf": uf, "bairro": bairro,
            "demografico": demo, "concorrencia": conc, "viabilidade": viab,
            "agregacao": bairro_veredito}


def _print_tree(m: dict[str, Any]) -> None:
    def L(leaf):  # noqa: E743
        return f"{leaf['valor']} [{leaf['categoria']}] {leaf['fonte']}"

    d = m["demografico"]
    sd = d["score_demografico"]
    print(f"=== METODOLOGIA: {m['cidade']}/{m['uf']} {m.get('bairro') or ''} ===")
    print(f"\n[A2 DEMOGRAFICO]  score = {sd['score']}  ({d['classificacao']})")
    print(f"  pop_total {d['populacao_total']} | pop_faixa {d['populacao_faixa']} | publico_potencial {d['publico_potencial']}")
    print(f"  faixa_pct        : {L(d['fonte_dados']['faixa_pct'])}")
    print(f"  publico_pot_taxa : {L(d['fonte_dados']['publico_potencial_taxa'])}")
    print(f"  renda_fonte      : {d['fonte_dados']['renda']}  (R$ {d['renda_media']})")
    cp = sd["componentes"]
    print(f"  + pts_pop {cp['pop_faixa']['pts']}  <- {L(cp['pop_faixa']['cutoff']) if isinstance(cp['pop_faixa']['cutoff'], dict) else cp['pop_faixa']['cutoff']}")
    print(f"  + pts_renda {cp['renda_media']['pts']}  <- {L(cp['renda_media']['cutoff']) if isinstance(cp['renda_media']['cutoff'], dict) else cp['renda_media']['cutoff']}")
    print(f"  + base {cp['base']['valor']} [{cp['base']['categoria']}]")

    c = m["concorrencia"]
    print(f"\n[A3 CONCORRENCIA] score = {c['score']}  (saturacao {c['saturacao']}, densidade {c['densidade_km2']}/km2)")
    print(f"  bonus_saturacao  : {L(c['componentes']['bonus_saturacao'])}")
    print(f"  penalidade_qtd   : {c['componentes']['penalidade_qtd']['valor']}  (fator {c['componentes']['penalidade_qtd']['fator']['valor']}, teto {c['componentes']['penalidade_qtd']['teto']['valor']})")
    print(f"  penalidade_rating: {c['componentes']['penalidade_rating']['valor']}")

    v = m["viabilidade"]
    cpv = v["componentes"]
    print(f"\n[A4 VIABILIDADE]  score = {v['score']}")
    print(f"  + pts_payback {cpv['payback_meses']['pts']}  <- {L(cpv['payback_meses']['cutoff']) if isinstance(cpv['payback_meses']['cutoff'], dict) else cpv['payback_meses']['cutoff']}")
    print(f"  + pts_ocupacao {cpv['ocupacao_break']['pts']}  <- {L(cpv['ocupacao_break']['cutoff']) if isinstance(cpv['ocupacao_break']['cutoff'], dict) else cpv['ocupacao_break']['cutoff']}")

    ag = m["agregacao"]
    print(f"\n[A6 AGREGACAO]")
    print(f"  score_bairro          = {ag['score_bairro']}  = {ag['formula_bairro']}")
    print(f"  score_top1_candidato  = {ag['score_top1_candidato']}  = {ag['formula_top1']}")
    print(f"  dimensoes: {ag['dimensoes']}")
    ver = ag["veredito"]
    print(f"\n[VEREDITO] {ver['veredito']}  (score_decisao {ver['score_decisao']})")
    print(f"  cutoff disparado: {L(ver['cutoff_disparado']) if isinstance(ver['cutoff_disparado'], dict) else ver['cutoff_disparado']}")


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    # Exemplo Cocó: demografico real (IBGE/Censo); concorrencia/viab = inputs ilustrativos
    # do pipeline (em produção A3 traz nº concorrentes/rating; A4 traz payback/ocupação).
    m = explicar_metodologia(
        "Fortaleza", "CE", bairro="Cocó",
        num_concorrentes=12, rating_medio=4.3, raio_km=3.0,
        payback_meses=28, ocupacao_break=0.45, geoscout_top1=7.0,
    )
    _print_tree(m)
