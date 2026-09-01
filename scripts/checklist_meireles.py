"""Checklist pós-run Meireles (Run 1/4) + dashboard vs Cocó."""
from __future__ import annotations

import json
import sys
from pathlib import Path

COCO = Path("metrics/relatorios/rpt_1786416027.json")


def _load(p: Path):
    d = json.loads(p.read_text(encoding="utf-8"))
    return d, d.get("output_consolidado") or {}


def _find_latest_meireles() -> Path:
    files = sorted(Path("metrics/relatorios").glob("rpt_*.json"), key=lambda x: x.stat().st_mtime)
    for p in reversed(files):
        try:
            d, oc = _load(p)
        except Exception:
            continue
        mc = oc.get("market_context") or {}
        bairro = (mc.get("bairro") or oc.get("bairro") or "").lower()
        if "meireles" in bairro:
            return p
        # fallback: input canônico
        inp = d.get("input") or d.get("input_canonico") or {}
        if "meireles" in str(inp.get("bairro") or "").lower():
            return p
    raise SystemExit("Nenhum rpt_* Meireles encontrado em metrics/relatorios")


def gated(oc):
    an = oc.get("aneis_competitivos") or {}
    cross = an.get("cross_check") if isinstance(an, dict) else {}
    return (cross or {}).get("gated_n")


def a4_block(d, oc):
    fin = (
        oc.get("analise_financeira")
        or oc.get("viabilidade_3_cenarios")
        or d.get("analise_financeira")
        or {}
    )
    if isinstance(fin.get("analise_financeira"), dict):
        fin = fin["analise_financeira"]
    if isinstance(fin.get("viabilidade_3_cenarios"), dict):
        # keep outer
        pass
    cens = fin.get("cenarios") or fin.get("viabilidade_3_cenarios") or {}
    if isinstance(cens, dict) and "cenarios" in cens:
        cens = cens["cenarios"]
    viab = {}
    if isinstance(cens, dict):
        for k in ("low", "mid", "premium"):
            c = cens.get(k) or {}
            viab[k] = c.get("viabilidade") if isinstance(c, dict) else None
    modelo = (
        oc.get("modelo_recomendado")
        or fin.get("recomendacao")
        or fin.get("recomendacao_modelo")
        or fin.get("modelo_recomendado")
    )
    return {
        "modelo": modelo,
        "alerta": fin.get("alerta_viabilidade"),
        "viabilidades": viab,
        "tem_3_cenarios": all(k in (cens or {}) for k in ("low", "mid", "premium"))
        if isinstance(cens, dict)
        else False,
    }


def a9_block(d, oc):
    pos = d.get("posicionamento_estrategico") or oc.get("posicionamento_estrategico") or {}
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
    return {
        "veredito": pos.get("veredito_posicionamento"),
        "fonte_veredito": pos.get("fonte_veredito"),
        "ticket": tk.get("ticket_recomendado"),
        "modelo_a4": pos.get("modelo_a4"),
        "confianca": tk.get("confianca"),
    }


def a8_block(d, oc):
    v = d.get("validacao_cruzada") or oc.get("validacao_cruzada") or {}
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except Exception:
            v = {}
    if not isinstance(v, dict):
        return {"status": None, "criticos": 0, "altas": 0, "alertas": []}
    alertas = v.get("alertas") or v.get("alertas_validacao") or []
    crit = altas = 0
    heads = []
    for a in alertas:
        if isinstance(a, dict):
            sev = str(a.get("severidade") or a.get("nivel") or "").upper()
            heads.append(f"{sev}:{(a.get('codigo') or a.get('mensagem') or '')[:80]}")
        else:
            heads.append(str(a)[:100])
            sev = str(a).upper()
        if "CRIT" in sev:
            crit += 1
        elif "ALTA" in sev or "HIGH" in sev:
            altas += 1
    return {
        "status": v.get("status_validacao") or v.get("status") or v.get("veredito"),
        "criticos": crit,
        "altas": altas,
        "n": len(alertas),
        "alertas": heads[:8],
    }


def genero_block(oc):
    m = oc.get("market_context") or {}
    ge = m.get("genero_estrategia") or oc.get("genero_estrategia") or {}
    if not isinstance(ge, dict):
        ge = {}
    return {
        "genero_alvo": m.get("genero_alvo") or oc.get("genero_alvo"),
        "estrategia": ge,
        "sobrescrito": ge.get("sobrescrito"),
        "faixa": (m.get("faixa_etaria_predominante") or "")[:100],
    }


def matriz_block(oc):
    m = oc.get("matriz_demo_saturacao") or {}
    return {
        "quadrante": m.get("quadrante"),
        "n_per_10k": m.get("n_per_10k"),
        "n_poligono": m.get("n_poligono"),
        "censo_base": m.get("censo_base"),
    }


def vias_block(oc):
    mv = oc.get("melhores_vias_prospeccao") or {}
    vias = mv.get("top_vias") if isinstance(mv, dict) else None
    top = (vias or [None])[0] if isinstance(vias, list) else None
    if isinstance(top, dict):
        return {
            "nome": top.get("nome_via") or top.get("nome") or top.get("via"),
            "score": top.get("fluxo_score") or top.get("score") or top.get("score_norm"),
            "n": len(vias or []),
        }
    fp = oc.get("fluxo_pedestre") or {}
    segs = fp.get("top_segments") or []
    if segs and isinstance(segs[0], dict):
        return {
            "nome": segs[0].get("name") or segs[0].get("nome"),
            "score": segs[0].get("score"),
            "n": len(segs),
        }
    return {"nome": None, "score": None, "n": 0}


def athletic_or_ig(d, oc):
    of = d.get("oferta_concorrentes") or oc.get("oferta_concorrentes") or {}
    inner = of.get("oferta_concorrentes") if isinstance(of.get("oferta_concorrentes"), dict) else of
    if not isinstance(inner, dict):
        return {"n_com_faixa": 0, "n_com_planos": 0, "amostras": []}
    n_faixa = n_planos = n_ig = 0
    amostras = []
    for k, v in inner.items():
        if not isinstance(v, dict):
            continue
        fontes = v.get("fontes") or []
        has_ig = "instagram" in [str(x).lower() for x in fontes] or bool(
            v.get("instagram_username") or v.get("highlights_gemini")
        )
        if has_ig:
            n_ig += 1
        if v.get("faixa_preco_brl"):
            n_faixa += 1
        planos = v.get("planos_extraidos") or []
        if planos:
            n_planos += 1
        if has_ig or v.get("faixa_preco_brl"):
            amostras.append(
                {
                    "nome": (v.get("nome") or k)[:50],
                    "faixa": v.get("faixa_preco_brl"),
                    "n_planos": len(planos) if isinstance(planos, list) else 0,
                    "fontes": fontes,
                    "ig": v.get("instagram_username"),
                    "conf": v.get("confiabilidade_oferta"),
                }
            )
    return {
        "n_ofertas": len(inner),
        "n_ig": n_ig,
        "n_com_faixa": n_faixa,
        "n_com_planos": n_planos,
        "amostras": amostras[:5],
    }


def cands(oc):
    t = oc.get("top_3_candidatos") or []
    out = []
    for c in (t or [])[:3]:
        if isinstance(c, dict):
            out.append(
                {
                    "nome": (c.get("nome") or "")[:60],
                    "area": c.get("area_m2") or c.get("area_estimada_m2"),
                    "modalidade": c.get("modalidade"),
                }
            )
    return out, oc.get("modo_prospeccao")


def demo(oc):
    d = oc.get("demografia_bairro") or oc.get("demografia") or {}
    if not isinstance(d, dict):
        d = {}
    return {
        "renda": d.get("renda_per_capita") or d.get("renda_media") or oc.get("renda_per_capita"),
        "pop": d.get("populacao") or d.get("pop_total") or oc.get("populacao"),
        "keys": sorted(list(d.keys()))[:12] if d else [],
    }


def mark(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def checklist(path: Path):
    d, oc = _load(path)
    mc = oc.get("market_context") or {}
    a4 = a4_block(d, oc)
    a9 = a9_block(d, oc)
    a8 = a8_block(d, oc)
    gen = genero_block(oc)
    mat = matriz_block(oc)
    vias = vias_block(oc)
    ofe = athletic_or_ig(d, oc)
    cand_list, modo = cands(oc)
    dem = demo(oc)

    all_inviavel = (
        bool(a4["viabilidades"])
        and all(v == "INVIAVEL" for v in a4["viabilidades"].values() if v)
        and len([v for v in a4["viabilidades"].values() if v]) == 3
    )
    modelo_nenhum = str(a4["modelo"] or "").lower() == "nenhum"

    items = []

    # 1 estrutura
    items.append(("1.1 output_consolidado presente", bool(oc)))
    items.append(
        (
            "1.2 market_context cidade/bairro/uf",
            str(mc.get("cidade") or "").lower() == "fortaleza"
            and "meireles" in str(mc.get("bairro") or "").lower()
            and str(mc.get("uf") or "").upper() == "CE",
        )
    )
    items.append(
        (
            "1.3 demografia_bairro com renda/pop",
            dem["renda"] is not None or dem["pop"] is not None or bool(dem["keys"]),
        )
    )
    items.append(("1.4 viabilidade 3 cenarios", a4["tem_3_cenarios"] or bool(a4["viabilidades"])))

    # 2 P1
    items.append(
        (
            "2.1 todos INVIAVEL => modelo nenhum",
            (not all_inviavel) or modelo_nenhum,
        )
    )
    items.append(
        (
            "2.2 modelo nenhum => ticket null",
            (not modelo_nenhum) or (a9["ticket"] is None),
        )
    )
    items.append(
        (
            "2.3 INDETERMINADO => sem ticket",
            (a9["veredito"] != "INDETERMINADO") or (a9["ticket"] is None),
        )
    )
    items.append(("2.4 top_3_candidatos vazio", len(cand_list) == 0))

    # 3 P2
    ge = gen["estrategia"] or {}
    items.append(
        (
            "3.1 genero com regra 8pp",
            bool(gen["genero_alvo"]) and (ge.get("limiar_pp") == 8.0 or ge.get("diff_pp") is not None),
        )
    )
    items.append(
        (
            "3.2 sobrescrito se input!=resultado",
            (ge.get("genero_input") == ge.get("genero_final")) or bool(ge.get("sobrescrito")),
        )
    )
    items.append(("3.3 n_per_10k calculado", mat.get("n_per_10k") is not None))

    # 4 L3.6
    items.append(
        (
            "4.1 IG => faixa/planos (se houver IG)",
            ofe["n_ig"] == 0 or (ofe["n_com_faixa"] > 0 or ofe["n_com_planos"] > 0),
        )
    )
    items.append(
        (
            "4.2 planos sanitizados (amostra)",
            ofe["n_com_planos"] == 0
            or any(
                isinstance((a.get("faixa") or {}), dict)
                and ((a["faixa"] or {}).get("min") or 0) < 800
                for a in ofe["amostras"]
            )
            or ofe["n_com_faixa"] > 0,
        )
    )
    items.append(
        (
            "4.3 faixa_preco se planos",
            ofe["n_com_planos"] == 0 or ofe["n_com_faixa"] > 0,
        )
    )

    # 5 A8
    items.append(("5.1 0 alertas CRÍTICOS", a8["criticos"] == 0))
    items.append(("5.2 ALTA ≤ 2", a8["altas"] <= 2))
    status = str(a8["status"] or "")
    items.append(
        (
            "5.3 status != REPROVADO_VALIDACAO (ou so ALTA)",
            "REPROVADO" not in status.upper() or a8["criticos"] == 0,
        )
    )

    print(f"=== CHECKLIST Meireles — {path.name} ===")
    print(f"uuid={d.get('relatorio_id') or d.get('id') or oc.get('relatorio_id')}")
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
                "saturacao": oc.get("nivel_saturacao") or oc.get("nivel_saturacao_bairro"),
                "gated_n": gated(oc),
                "n_trad": oc.get("total_concorrentes_analisados"),
                "modelo_a4": a4["modelo"],
                "viabilidades": a4["viabilidades"],
                "alerta_a4": a4["alerta"],
                "a9": a9,
                "a8": a8,
                "genero": gen,
                "matriz": mat,
                "vias": vias,
                "aluguel": oc.get("aluguel_mensal"),
                "fonte_aluguel": oc.get("fonte_aluguel"),
                "renda": dem,
                "cands": cand_list,
                "modo_prospeccao": modo,
                "oferta_ig": {
                    k: ofe[k] for k in ("n_ofertas", "n_ig", "n_com_faixa", "n_com_planos", "amostras")
                },
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )

    # dashboard vs coco
    if COCO.exists():
        cd, coc = _load(COCO)
        ca4 = a4_block(cd, coc)
        ca9 = a9_block(cd, coc)
        cgen = genero_block(coc)
        cmat = matriz_block(coc)
        cvias = vias_block(coc)
        print()
        print("--- DASHBOARD vs Cocó ---")
        rows = [
            ("Veredito", coc.get("veredito"), oc.get("veredito")),
            ("Modelo A4", ca4["modelo"], a4["modelo"]),
            ("Ticket A9", ca9["ticket"], a9["ticket"]),
            (
                "Saturação",
                f"{coc.get('nivel_saturacao')} ({gated(coc)} gated)",
                f"{oc.get('nivel_saturacao') or oc.get('nivel_saturacao_bairro')} ({gated(oc)} gated)",
            ),
            ("Aluguel MRLR", coc.get("aluguel_mensal"), oc.get("aluguel_mensal")),
            ("Gênero", cgen.get("genero_alvo"), gen.get("genero_alvo")),
            ("n_per_10k", cmat.get("n_per_10k"), mat.get("n_per_10k")),
            (
                "Top-1 via",
                f"{cvias.get('nome')} ({cvias.get('score')})",
                f"{vias.get('nome')} ({vias.get('score')})",
            ),
            ("A8 críticos", a8_block(cd, coc)["criticos"], a8["criticos"]),
        ]
        print(f"{'Métrica':20} | {'Cocó':40} | Meireles")
        for name, a, b in rows:
            print(f"{name:20} | {str(a)[:40]:40} | {b}")

    fails = sum(1 for _, ok in items if not ok)
    return 0 if fails == 0 else 1


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else _find_latest_meireles()
    return checklist(path)


if __name__ == "__main__":
    raise SystemExit(main())
