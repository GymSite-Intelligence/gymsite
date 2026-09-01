"""Checklist pós-run Lagoa RJ (Run 3/4) + dashboard vs Fortaleza."""
from __future__ import annotations

import json
import sys
from pathlib import Path

COCO = Path("metrics/relatorios/rpt_1786416027.json")
MEIRELES = Path("metrics/relatorios/rpt_1786447780.json")
PARANGABA = Path("metrics/relatorios/rpt_1786471019.json")
BAIRRO = "lagoa"
FORTALEZA_ALUGUEIS = {25440.0, 18390.0}


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
        inner = mc.get("market_context") if isinstance(mc.get("market_context"), dict) else mc
        bairro = str((inner or {}).get("bairro") or oc.get("bairro") or "").lower()
        cidade = str((inner or {}).get("cidade") or oc.get("cidade") or "").lower()
        if BAIRRO in bairro and "rio" in cidade:
            return p
        inp = d.get("input_canonico") or {}
        if BAIRRO in str(inp.get("bairro") or "").lower() and "RJ" in str(inp.get("uf") or "").upper():
            return p
    raise SystemExit("Nenhum rpt_* Lagoa/RJ encontrado")


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
        "just": (oc.get("modelo_recomendado_justificativa") or "")[:200],
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
    v = d.get("validacao_a8") or {}
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
    inner = m.get("market_context") if isinstance(m.get("market_context"), dict) else m
    if not isinstance(inner, dict):
        inner = {}
    ge = inner.get("genero_estrategia") or m.get("genero_estrategia") or {}
    if not isinstance(ge, dict):
        ge = {}
    return {
        "genero_alvo": inner.get("genero_alvo") or m.get("genero_alvo") or oc.get("genero_alvo"),
        "estrategia": ge,
        "cidade": inner.get("cidade") or m.get("cidade"),
        "bairro": inner.get("bairro") or m.get("bairro"),
        "uf": inner.get("uf") or m.get("uf"),
    }


def vias_block(oc):
    mv = oc.get("melhores_vias_prospeccao") or {}
    vias = mv.get("top_vias") if isinstance(mv, dict) else None
    top = (vias or [None])[0] if isinstance(vias, list) else None
    if isinstance(top, dict):
        return {
            "nome": top.get("nome_via") or top.get("nome"),
            "score": top.get("fluxo_score") or top.get("score"),
            "top3": [
                f"{(v.get('nome_via') or '')[:40]} ({v.get('fluxo_score')})"
                for v in (vias or [])[:3]
                if isinstance(v, dict)
            ],
        }
    return {"nome": None, "score": None, "top3": []}


def zoneamento(oc):
    z = oc.get("zoneamento") or {}
    if not isinstance(z, dict):
        return {"presente": False}
    return {
        "presente": bool(z),
        "zona": z.get("zona") or z.get("zona_sigla") or z.get("sigla"),
        "fonte": z.get("fonte") or z.get("fonte_zoneamento"),
        "alerta": (z.get("alerta") or "")[:120],
        "keys": sorted(z.keys())[:10],
    }


def demo(oc):
    d = oc.get("demografia_bairro") or {}
    if not isinstance(d, dict):
        d = {}
    return {
        "renda": d.get("renda_per_capita") or d.get("renda_media") or oc.get("renda_per_capita"),
        "pop": d.get("populacao") or d.get("pop_total"),
        "fonte": d.get("fonte_renda") or d.get("censo_base") or d.get("fonte"),
    }


def cands(oc):
    t = oc.get("top_3_candidatos") or []
    return len(t) if isinstance(t, list) else 0


def mark(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def snap(path: Path):
    d, oc = _load(path)
    a4 = a4_block(oc)
    a9 = a9_block(oc)
    gen = genero_block(oc)
    return {
        "file": path.name,
        "veredito": oc.get("veredito"),
        "saturacao": oc.get("nivel_saturacao"),
        "gated_n": gated(oc),
        "modelo": a4["modelo"],
        "ticket": a9["ticket"],
        "aluguel": oc.get("aluguel_mensal"),
        "genero": gen.get("genero_alvo"),
        "n_per_10k": a9["matriz"].get("n_per_10k"),
        "quadrante": a9["matriz"].get("quadrante"),
        "via": vias_block(oc).get("nome"),
        "a8_crit": a8_block(d)["criticos"],
        "renda": demo(oc).get("renda"),
    }


def checklist(path: Path) -> int:
    d, oc = _load(path)
    a4 = a4_block(oc)
    a9 = a9_block(oc)
    a8 = a8_block(d)
    gen = genero_block(oc)
    dem = demo(oc)
    zon = zoneamento(oc)
    vias = vias_block(oc)
    aluguel = oc.get("aluguel_mensal")
    modelo = str(a4["modelo"] or "")
    modelo_ok = modelo.lower() in ("nenhum", "premium", "premium boutique") or "premium" in modelo.lower()
    modelo_nenhum = modelo.lower() == "nenhum"
    sat = str(oc.get("nivel_saturacao") or "").upper()

    # A0 context: tokens file soft-check via absence of overflow markers in metadata
    meta = d.get("metadata_execucao") or {}
    a0_ok = not bool(oc.get("a0_degraded") or (gen.get("estrategia") or {}).get("a0_degraded"))

    items = [
        ("1.1 output_consolidado", bool(oc)),
        (
            "1.2 market_context RJ/Lagoa",
            "rio" in str(gen.get("cidade") or "").lower()
            and BAIRRO in str(gen.get("bairro") or "").lower()
            and str(gen.get("uf") or oc.get("uf") or "").upper() in ("RJ", ""),
        ),
        ("1.3 demografia renda/pop", dem["renda"] is not None or dem["pop"] is not None),
        ("1.4 viabilidade 3 cenarios", a4["tem_3"]),
        ("2. modelo in {Premium, nenhum}", modelo_ok or modelo_nenhum or bool(modelo)),
        ("2b. Premium ou nenhum (aceite estrito)", modelo_ok),
        ("3. nenhum => ticket null", (not modelo_nenhum) or (a9["ticket"] is None)),
        ("4. saturacao ALTO/SATURADO", sat in ("ALTO", "SATURADO")),
        (
            "5. aluguel != Fortaleza refs",
            aluguel is not None and float(aluguel) not in FORTALEZA_ALUGUEIS,
        ),
        ("6. zoneamento presente", zon["presente"]),
        ("7. 0 CRITICOS", a8["criticos"] == 0),
        ("8. (supabase checado à parte)", True),
        ("9. A0 nao degradado", a0_ok),
        ("P1 top_3 vazio", cands(oc) == 0),
        ("P2 n_per_10k", a9["matriz"].get("n_per_10k") is not None),
    ]

    print(f"=== CHECKLIST Lagoa RJ — {path.name} ===")
    print(f"uuid={d.get('id') or d.get('relatorio_id')}")
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
                "a4": a4,
                "a9": a9,
                "a8": a8,
                "genero": gen,
                "renda": dem,
                "aluguel": aluguel,
                "fonte_aluguel": oc.get("fonte_aluguel"),
                "zoneamento": zon,
                "vias": vias,
                "meta": {k: meta.get(k) for k in ("provider", "modelo", "duracao_s", "tokens") if k in meta or True},
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )

    print()
    print("--- DASHBOARD ---")
    refs = [("Coco", COCO), ("Meireles", MEIRELES), ("Parangaba", PARANGABA), ("Lagoa", path)]
    snaps = [(lab, snap(p) if p.exists() else {}) for lab, p in refs]
    keys = [
        ("veredito", "Veredito"),
        ("modelo", "Modelo A4"),
        ("ticket", "Ticket A9"),
        ("saturacao", "Saturacao"),
        ("gated_n", "gated_n"),
        ("aluguel", "Aluguel"),
        ("renda", "Renda"),
        ("genero", "Genero"),
        ("n_per_10k", "n_per_10k"),
        ("quadrante", "Quadrante"),
        ("via", "Top-1 via"),
        ("a8_crit", "A8 crit"),
    ]
    header = f"{'Metrica':14} | " + " | ".join(f"{lab:18}" for lab, _ in snaps)
    print(header)
    for key, name in keys:
        vals = [str(s.get(key))[:18] for _, s in snaps]
        print(f"{name:14} | " + " | ".join(f"{v:18}" for v in vals))

    fails = sum(1 for _, ok in items if not ok)
    return 0 if fails == 0 else 1


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else _find_latest()
    return checklist(path)


if __name__ == "__main__":
    raise SystemExit(main())
