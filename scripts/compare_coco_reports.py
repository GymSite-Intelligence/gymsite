"""Compare Cocó reports before/after P0–P2."""
from __future__ import annotations

import json
import sys
from pathlib import Path

OLD = Path("metrics/relatorios/rpt_1786399356.json")
NEW = Path("metrics/relatorios/rpt_1786416027.json")


def load(p: Path):
    d = json.loads(p.read_text(encoding="utf-8"))
    return d, d.get("output_consolidado") or {}


def gated(oc):
    an = oc.get("aneis_competitivos") or {}
    cross = an.get("cross_check") if isinstance(an, dict) else {}
    return (cross or {}).get("gated_n")


def fluxo_top(oc):
    mv = oc.get("melhores_vias_prospeccao") or {}
    vias = mv.get("top_vias") if isinstance(mv, dict) else None
    if isinstance(vias, list) and vias:
        v = vias[0]
        return (
            v.get("nome") or v.get("via"),
            v.get("score") or v.get("fluxo_score") or v.get("score_norm"),
        )
    fp = oc.get("fluxo_pedestre") or {}
    segs = fp.get("top_segments") or []
    if segs:
        return segs[0].get("name") or segs[0].get("nome"), segs[0].get("score")
    return None, None


def athletic(d, oc):
    of = d.get("oferta_concorrentes") or oc.get("oferta_concorrentes") or {}
    inner = of.get("oferta_concorrentes") if isinstance(of.get("oferta_concorrentes"), dict) else of
    if not isinstance(inner, dict):
        return {}
    for k, v in inner.items():
        if isinstance(v, dict) and "athletic" in str(v.get("nome") or k).lower():
            return {
                kk: v.get(kk)
                for kk in (
                    "nome",
                    "faixa_preco_brl",
                    "fontes",
                    "confiabilidade_oferta",
                    "planos_extraidos",
                    "modalidades",
                    "instagram_username",
                )
            }
    return {}


def a9(d, oc):
    pos = d.get("posicionamento_estrategico") or oc.get("posicionamento_estrategico") or {}
    if isinstance(pos, str):
        try:
            pos = json.loads(pos)
        except Exception:
            pos = {}
    tk = (pos.get("recomendacao_ticket") or {}) if isinstance(pos, dict) else {}
    return {
        "veredito": pos.get("veredito_posicionamento") if isinstance(pos, dict) else None,
        "fonte_veredito": pos.get("fonte_veredito") if isinstance(pos, dict) else None,
        "ticket": tk.get("ticket_recomendado"),
        "confianca": tk.get("confianca"),
        "modelo_a4": pos.get("modelo_a4"),
    }


def a4(oc):
    fin = oc.get("analise_financeira") or {}
    if isinstance(fin.get("analise_financeira"), dict):
        fin = fin["analise_financeira"]
    cens = fin.get("cenarios") or {}
    viab = {
        k: (cens.get(k) or {}).get("viabilidade")
        for k in ("low", "mid", "premium")
        if isinstance(cens, dict)
    }
    return {
        "recomendacao": fin.get("recomendacao")
        or fin.get("recomendacao_modelo")
        or fin.get("modelo_recomendado"),
        "alerta_viabilidade": fin.get("alerta_viabilidade"),
        "viabilidades": viab,
        "score": fin.get("score_viabilidade"),
    }


def a8(d, oc):
    v = d.get("validacao_cruzada") or oc.get("validacao_cruzada") or {}
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except Exception:
            v = {}
    if not isinstance(v, dict):
        return {}
    return {
        "score": v.get("score_validacao"),
        "status": v.get("status") or v.get("veredito"),
        "n_alertas": len(v.get("alertas") or []),
        "alertas_head": [str(a)[:100] for a in (v.get("alertas") or [])[:5]],
    }


def mc(oc):
    m = oc.get("market_context") or {}
    return {
        "genero_alvo": m.get("genero_alvo"),
        "genero_estrategia": m.get("genero_estrategia"),
        "faixa": (m.get("faixa_etaria_predominante") or "")[:80],
    }


def matriz(oc):
    m = oc.get("matriz_demo_saturacao") or {}
    return {k: m.get(k) for k in ("quadrante", "n_per_10k", "n_poligono", "censo_base")}


def cands(oc):
    t = oc.get("top_3_candidatos") or []
    out = []
    for c in t[:3]:
        if isinstance(c, dict):
            out.append(
                {
                    "nome": (c.get("nome") or "")[:55],
                    "area": c.get("area_m2") or c.get("area_estimada_m2"),
                    "modalidade": c.get("modalidade"),
                }
            )
    return out, oc.get("modo_prospeccao")


def snap(path: Path):
    d, oc = load(path)
    via, score = fluxo_top(oc)
    return {
        "file": path.name,
        "veredito": oc.get("veredito"),
        "saturacao": oc.get("nivel_saturacao"),
        "gated_n": gated(oc),
        "n_trad": oc.get("total_concorrentes_analisados"),
        "modelo_rec": oc.get("modelo_recomendado"),
        "fonte_aluguel": oc.get("fonte_aluguel"),
        "aluguel": oc.get("aluguel_mensal"),
        "via_top1": via,
        "via_score": score,
        "matriz": matriz(oc),
        "a4": a4(oc),
        "a9": a9(d, oc),
        "a8": a8(d, oc),
        "genero": mc(oc),
        "athletic": athletic(d, oc),
        "cands": cands(oc),
    }


def main() -> int:
    old, new = snap(OLD), snap(NEW)
    print("=== COMPARACAO Coco ===")
    print(f"OLD {OLD.name}")
    print(f"NEW {NEW.name} (uuid de2bdfd1, ~399s)")
    print()
    for k in (
        "veredito",
        "saturacao",
        "gated_n",
        "n_trad",
        "modelo_rec",
        "fonte_aluguel",
        "aluguel",
        "via_top1",
        "via_score",
    ):
        o, n = old.get(k), new.get(k)
        mark = "  " if o == n else "!="
        print(f"{mark} {k:20} | {str(o)[:45]:45} | {str(n)[:45]}")
    print()
    print("MATRIZ OLD", old["matriz"])
    print("MATRIZ NEW", new["matriz"])
    print()
    print("A4 OLD", old["a4"])
    print("A4 NEW", new["a4"])
    print()
    print("A9 OLD", old["a9"])
    print("A9 NEW", new["a9"])
    print()
    print("A8 OLD", old["a8"])
    print("A8 NEW", new["a8"])
    print()
    print("GENERO OLD", old["genero"])
    print("GENERO NEW", new["genero"])
    print()
    print("ATHLETIC OLD", json.dumps(old["athletic"], ensure_ascii=False)[:600])
    print("ATHLETIC NEW", json.dumps(new["athletic"], ensure_ascii=False)[:900])
    print()
    print("CANDS OLD", old["cands"])
    print("CANDS NEW", new["cands"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
