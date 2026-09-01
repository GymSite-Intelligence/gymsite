"""Checklist pós-run Parangaba (Run 2/4) + dashboard vs Cocó/Meireles."""
from __future__ import annotations

import json
import sys
from pathlib import Path

COCO = Path("metrics/relatorios/rpt_1786416027.json")
MEIRELES = Path("metrics/relatorios/rpt_1786447780.json")
BAIRRO = "parangaba"


def _load(p: Path):
    d = json.loads(p.read_text(encoding="utf-8"))
    return d, d.get("output_consolidado") or {}


def _find_latest() -> Path:
    files = sorted(Path("metrics/relatorios").glob("rpt_*.json"), key=lambda x: x.stat().st_mtime)
    for p in reversed(files):
        try:
            d, oc = _load(p)
        except Exception:
            continue
        mc = oc.get("market_context") or {}
        bairro = (mc.get("bairro") or oc.get("bairro") or "").lower()
        if BAIRRO in bairro:
            return p
        inp = d.get("input_canonico") or d.get("input") or {}
        if BAIRRO in str(inp.get("bairro") or "").lower():
            return p
    raise SystemExit(f"Nenhum rpt_* {BAIRRO} encontrado")


def gated(oc):
    an = oc.get("aneis_competitivos") or {}
    cross = an.get("cross_check") if isinstance(an, dict) else {}
    return (cross or {}).get("gated_n")


def a4_block(oc):
    v3 = oc.get("viabilidade_3_cenarios") or {}
    viab = {}
    if isinstance(v3, dict):
        for k in ("low", "mid", "premium"):
            c = v3.get(k) or {}
            viab[k] = c.get("viabilidade") if isinstance(c, dict) else None
    return {
        "modelo": oc.get("modelo_recomendado"),
        "viabilidades": viab,
        "tem_3": all(k in v3 for k in ("low", "mid", "premium")) if isinstance(v3, dict) else False,
        "just": (oc.get("modelo_recomendado_justificativa") or "")[:180],
    }


def a9_block(oc):
    pos = oc.get("posicionamento_estrategico") or {}
    if isinstance(pos, str):
        try:
            pos = json.loads(pos)
        except Exception:
            pos = {}
    if not isinstance(pos, dict):
        pos = {}
    tk = pos.get("recomendacao_ticket") or {}
    if not isinstance(tk, dict):
        tk = {}
    mat = pos.get("matriz_demo_saturacao") or oc.get("matriz_demo_saturacao") or {}
    return {
        "veredito": pos.get("veredito_posicionamento"),
        "fonte_veredito": pos.get("fonte_veredito"),
        "ticket": tk.get("ticket_recomendado"),
        "modelo_a4": pos.get("modelo_a4"),
        "matriz": {
            "quadrante": mat.get("quadrante"),
            "n_per_10k": mat.get("n_per_10k"),
            "n_poligono": mat.get("n_poligono"),
            "censo_base": mat.get("censo_base"),
        },
    }


def a8_block(d):
    v = d.get("validacao_a8") or d.get("validacao_cruzada") or {}
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except Exception:
            v = {}
    if not isinstance(v, dict):
        return {"status": None, "criticos": 0, "altas": 0, "n": 0, "alertas": []}
    alertas = v.get("alertas") or []
    crit = altas = 0
    heads = []
    for a in alertas:
        if isinstance(a, dict):
            sev = str(a.get("severidade") or a.get("nivel") or "").upper()
            heads.append(f"{sev}:{(a.get('tipo') or '')} {(a.get('descricao') or '')[:90]}")
        else:
            sev = str(a).upper()
            heads.append(str(a)[:100])
        if "CRIT" in sev:
            crit += 1
        elif "ALTA" in sev:
            altas += 1
    return {
        "status": v.get("status_validacao") or v.get("status"),
        "criticos": crit,
        "altas": altas,
        "n": len(alertas),
        "alertas": heads[:8],
        "score": v.get("score_validacao"),
    }


def genero_block(oc):
    m = oc.get("market_context") or {}
    ge = m.get("genero_estrategia") or {}
    if not isinstance(ge, dict):
        ge = {}
    return {
        "genero_alvo": m.get("genero_alvo") or oc.get("genero_alvo"),
        "estrategia": ge,
        "sobrescrito": ge.get("sobrescrito"),
    }


def vias_block(oc):
    mv = oc.get("melhores_vias_prospeccao") or {}
    vias = mv.get("top_vias") if isinstance(mv, dict) else None
    top = (vias or [None])[0] if isinstance(vias, list) else None
    if isinstance(top, dict):
        return {
            "nome": top.get("nome_via") or top.get("nome"),
            "score": top.get("fluxo_score") or top.get("score"),
            "n": len(vias or []),
            "top3": [
                f"{(v.get('nome_via') or '')[:40]} ({v.get('fluxo_score')})"
                for v in (vias or [])[:3]
                if isinstance(v, dict)
            ],
        }
    return {"nome": None, "score": None, "n": 0, "top3": []}


def oferta_block(d, oc):
    of = d.get("oferta_concorrentes") or oc.get("oferta_concorrentes") or {}
    inner = of.get("oferta_concorrentes") if isinstance(of.get("oferta_concorrentes"), dict) else of
    if not isinstance(inner, dict):
        return {"n": 0, "n_ig": 0, "n_faixa": 0, "n_planos": 0, "amostras": []}
    n_ig = n_faixa = n_planos = 0
    amostras = []
    for k, v in inner.items():
        if not isinstance(v, dict):
            continue
        fontes = v.get("fontes") or []
        has_ig = "instagram" in [str(x).lower() for x in fontes] or bool(v.get("instagram_username"))
        if has_ig:
            n_ig += 1
        if v.get("faixa_preco_brl"):
            n_faixa += 1
        planos = v.get("planos_extraidos") or []
        if planos:
            n_planos += 1
        amostras.append(
            {
                "nome": (v.get("nome") or k)[:45],
                "fontes": fontes,
                "ig": v.get("instagram_username"),
                "faixa": v.get("faixa_preco_brl"),
                "n_planos": len(planos) if isinstance(planos, list) else 0,
                "conf": v.get("confiabilidade_oferta"),
            }
        )
    return {
        "n": len(inner),
        "n_ig": n_ig,
        "n_faixa": n_faixa,
        "n_planos": n_planos,
        "amostras": amostras[:5],
    }


def demo(oc):
    d = oc.get("demografia_bairro") or {}
    if not isinstance(d, dict):
        d = {}
    return {
        "renda": d.get("renda_per_capita") or d.get("renda_media") or oc.get("renda_per_capita"),
        "pop": d.get("populacao") or d.get("pop_total"),
    }


def cands(oc):
    t = oc.get("top_3_candidatos") or []
    return [
        {
            "nome": (c.get("nome") or "")[:55],
            "area": c.get("area_m2") or c.get("area_estimada_m2"),
            "modalidade": c.get("modalidade"),
        }
        for c in (t or [])[:3]
        if isinstance(c, dict)
    ]


def mark(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def snap(path: Path):
    d, oc = _load(path)
    a4 = a4_block(oc)
    a9 = a9_block(oc)
    return {
        "file": path.name,
        "veredito": oc.get("veredito"),
        "saturacao": oc.get("nivel_saturacao"),
        "gated_n": gated(oc),
        "modelo": a4["modelo"],
        "ticket": a9["ticket"],
        "aluguel": oc.get("aluguel_mensal"),
        "genero": genero_block(oc).get("genero_alvo"),
        "n_per_10k": a9["matriz"].get("n_per_10k"),
        "via": vias_block(oc).get("nome"),
        "via_score": vias_block(oc).get("score"),
        "a8_crit": a8_block(d)["criticos"],
    }


def checklist(path: Path) -> int:
    d, oc = _load(path)
    mc = oc.get("market_context") or {}
    a4 = a4_block(oc)
    a9 = a9_block(oc)
    a8 = a8_block(d)
    gen = genero_block(oc)
    vias = vias_block(oc)
    ofe = oferta_block(d, oc)
    dem = demo(oc)
    cand_list = cands(oc)

    all_inviavel = (
        bool(a4["viabilidades"])
        and all(v == "INVIAVEL" for v in a4["viabilidades"].values() if v)
        and len([v for v in a4["viabilidades"].values() if v]) == 3
    )
    modelo_nenhum = str(a4["modelo"] or "").lower() == "nenhum"
    ge = gen["estrategia"] or {}

    items = [
        ("1.1 output_consolidado", bool(oc)),
        (
            "1.2 market_context cidade/bairro/uf",
            str(mc.get("cidade") or "").lower() == "fortaleza"
            and BAIRRO in str(mc.get("bairro") or "").lower()
            and str(mc.get("uf") or "").upper() == "CE",
        ),
        ("1.3 demografia renda/pop", dem["renda"] is not None or dem["pop"] is not None),
        ("1.4 viabilidade 3 cenarios", a4["tem_3"]),
        ("2.1 INVIAVEL => nenhum", (not all_inviavel) or modelo_nenhum),
        ("2.2 nenhum => ticket null", (not modelo_nenhum) or (a9["ticket"] is None)),
        ("2.3 INDETERMINADO => sem ticket", (a9["veredito"] != "INDETERMINADO") or (a9["ticket"] is None)),
        ("2.4 top_3_candidatos vazio", len(cand_list) == 0),
        (
            "3.1 genero regra 8pp",
            bool(gen["genero_alvo"]) and (ge.get("limiar_pp") == 8.0 or ge.get("diff_pp") is not None),
        ),
        (
            "3.2 sobrescrito se input!=resultado",
            (ge.get("genero_input") == ge.get("genero_final")) or bool(ge.get("sobrescrito")),
        ),
        ("3.3 n_per_10k", a9["matriz"].get("n_per_10k") is not None),
        (
            "4.1 IG => faixa/planos (se houver IG)",
            ofe["n_ig"] == 0 or (ofe["n_faixa"] > 0 or ofe["n_planos"] > 0),
        ),
        ("4.3 faixa se planos", ofe["n_planos"] == 0 or ofe["n_faixa"] > 0),
        ("5.1 0 CRITICOS", a8["criticos"] == 0),
        ("5.2 ALTA <= 2", a8["altas"] <= 2),
        (
            "5.3 status ok",
            "REPROVADO" not in str(a8["status"] or "").upper() or a8["criticos"] == 0,
        ),
    ]

    print(f"=== CHECKLIST Parangaba — {path.name} ===")
    print(f"uuid={d.get('id') or d.get('relatorio_id') or oc.get('relatorio_id')}")
    print()
    for label, ok in items:
        print(f"[{mark(ok)}] {label}")
    print()
    print("--- CAMPOS-CHAVE ---")
    print(
        json.dumps(
            {
                "file": path.name,
                "veredito": oc.get("veredito"),
                "saturacao": oc.get("nivel_saturacao"),
                "gated_n": gated(oc),
                "n_trad": oc.get("total_concorrentes_analisados"),
                "a4": a4,
                "a9": a9,
                "a8": a8,
                "genero": gen,
                "vias": vias,
                "aluguel": oc.get("aluguel_mensal"),
                "fonte_aluguel": oc.get("fonte_aluguel"),
                "renda": dem,
                "cands": cand_list,
                "oferta": ofe,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )

    rows = [("Metrica", "Coco", "Meireles", "Parangaba")]
    snaps = []
    for label, pth in (("Coco", COCO), ("Meireles", MEIRELES), ("Parangaba", path)):
        if pth.exists():
            snaps.append((label, snap(pth)))
        else:
            snaps.append((label, {}))
    keys = [
        ("veredito", "Veredito"),
        ("modelo", "Modelo A4"),
        ("ticket", "Ticket A9"),
        ("saturacao", "Saturacao"),
        ("gated_n", "gated_n"),
        ("aluguel", "Aluguel"),
        ("genero", "Genero"),
        ("n_per_10k", "n_per_10k"),
        ("via", "Top-1 via"),
        ("a8_crit", "A8 criticos"),
    ]
    print()
    print("--- DASHBOARD ---")
    print(f"{'Metrica':16} | {'Coco':28} | {'Meireles':28} | Parangaba")
    for key, name in keys:
        vals = [str(s.get(key))[:28] for _, s in snaps]
        print(f"{name:16} | {vals[0]:28} | {vals[1]:28} | {vals[2]}")

    fails = sum(1 for _, ok in items if not ok)
    return 0 if fails == 0 else 1


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else _find_latest()
    return checklist(path)


if __name__ == "__main__":
    raise SystemExit(main())
