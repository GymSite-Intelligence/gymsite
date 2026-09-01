"""
tests/diagnostico_coco.py

Diagnóstico das duas falhas do golden case Cocó.
Extrai dados do JSON fresco para decidir se corrige pipeline ou golden.

Uso: python tests/diagnostico_coco.py --json metrics/relatorios/rpt_1786376018.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def diagnosticar(json_path: str) -> dict:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    out = data.get("output_consolidado", {})
    resultado = {
        "veredito": out.get("veredito"),
        "score_bairro": out.get("score_bairro"),
        "nivel_saturacao": out.get("nivel_saturacao"),
        "total_concorrentes_analisados": out.get("total_concorrentes_analisados"),
    }

    # ── Falha 1: Saturação ──────────────────────────────────────────────
    intelig = data.get("inteligencia_competitiva") or {}
    concorrentes = intelig.get("concorrentes_detalhados") or []
    # Fallback: academias no output consolidado
    if not concorrentes:
        concorrentes = out.get("academias_analisadas") or out.get("competitors_set") or []
        if isinstance(concorrentes, dict):
            concorrentes = list(concorrentes.values()) if concorrentes else []
    resultado["total_concorrentes_detalhados"] = len(concorrentes)

    bairros_concorrentes: dict[str, int] = {}
    for c in concorrentes:
        if not isinstance(c, dict):
            continue
        bairro = (
            c.get("bairro_concorrente")
            or c.get("bairro")
            or c.get("bairro_normalizado")
            or "desconhecido"
        )
        bairros_concorrentes[bairro] = bairros_concorrentes.get(bairro, 0) + 1
    resultado["concorrentes_por_bairro"] = bairros_concorrentes

    dist_geo = intelig.get("distribuicao_geografica") or out.get("distribuicao_geografica") or []
    resultado["distribuicao_geografica"] = dist_geo

    # ── Falha 2: Fluxo ───────────────────────────────────────────────────
    fluxo = out.get("fluxo_pedestre") or data.get("fluxo_pedestre") or {}
    resultado["fluxo_pedestre"] = {
        "status": fluxo.get("status"),
        "confianca": fluxo.get("confianca"),
        "fluxo_score": fluxo.get("fluxo_score"),
        "fluxo_score_candidato": fluxo.get("fluxo_score_candidato") or fluxo.get("fluxo_score"),
        "fluxo_norm": fluxo.get("fluxo_norm"),
        "fluxo_segmento": fluxo.get("fluxo_segmento"),
        "statistics": fluxo.get("statistics"),
        "top_segments": (fluxo.get("top_segments") or [])[:3],
    }

    top_vias = out.get("top_vias_prospeccao") or data.get("top_vias_prospeccao") or {}
    if top_vias.get("status") == "ok":
        vias = top_vias.get("top_vias") or []
        resultado["top_vias_prospeccao"] = {
            "status": "ok",
            "n_vias": len(vias),
            "top_1": vias[0] if vias else None,
        }
        if vias:
            top1 = vias[0]
            nome = str(top1.get("nome_via") or top1.get("street_name") or "")
            resultado["top_vias_prospeccao"]["top_1_nome"] = nome
            resultado["top_vias_prospeccao"]["top_1_fluxo_score"] = top1.get("fluxo_score") or top1.get(
                "flow_score"
            )
            nome_l = nome.lower()
            resultado["top_vias_prospeccao"]["top_1_e_arteria"] = (
                "beira mar" in nome_l
                or "dom luís" in nome_l
                or "dom luis" in nome_l
            )
    else:
        # Fallback: top_segments do space syntax (mesmo que top_vias_prospeccao)
        segs = fluxo.get("top_segments") or []
        if segs:
            top1 = segs[0]
            nome = str(top1.get("street_name") or top1.get("nome_via") or "")
            score = top1.get("flow_score") or top1.get("fluxo_score")
            # flow_score em [0,1] → escala 0-100 se necessário
            if isinstance(score, (int, float)) and score <= 1.0:
                score_100 = round(float(score) * 100, 1)
            else:
                score_100 = score
            nome_l = nome.lower()
            resultado["top_vias_prospeccao"] = {
                "status": "ok_via_top_segments",
                "n_vias": len(segs),
                "top_1_nome": nome,
                "top_1_fluxo_score": score_100,
                "top_1_e_arteria": (
                    "beira mar" in nome_l
                    or "dom luís" in nome_l
                    or "dom luis" in nome_l
                    or "almirante" in nome_l
                    or "washington" in nome_l
                ),
                "fonte": "fluxo_pedestre.top_segments",
            }
        else:
            resultado["top_vias_prospeccao"] = {
                "status": top_vias.get("status", "ausente"),
                "motivo": top_vias.get("motivo"),
            }

    # ── Renda (sanidade) ────────────────────────────────────────────────
    demografia = out.get("demografia_bairro") or {}
    resultado["renda_bairro"] = {
        "renda_pc": demografia.get("renda_pc") or demografia.get("renda_media_bairro"),
        "percentil": demografia.get("percentil"),
        "fonte": demografia.get("fonte"),
    }

    return resultado


def analisar_falha_saturacao(diag: dict) -> dict:
    """Analisa se a saturação ALTO está correta ou se precisa calibrar."""
    n_concorrentes = diag.get("total_concorrentes_detalhados", 0)
    nivel = diag.get("nivel_saturacao")

    # Contagem no bairro Cocó (string match frouxo)
    por_bairro = diag.get("concorrentes_por_bairro") or {}
    n_coco = 0
    for bairro, count in por_bairro.items():
        bl = str(bairro).lower()
        if "coc" in bl:  # Cocó / Coco / Cocó / Guararapes
            n_coco += count

    analise = {
        "n_concorrentes_detalhados": n_concorrentes,
        "n_concorrentes_bairro_coco": n_coco,
        "nivel_saturacao": nivel,
        "diagnostico": None,
        "acao": None,
    }

    n_ref = n_coco if n_coco else n_concorrentes
    limiar_alto = 6
    limiar_saturado = 10

    if n_ref >= limiar_saturado and nivel != "SATURADO":
        analise["diagnostico"] = (
            f"Cocó tem {n_ref} tradicionais mas saturação é {nivel}. "
            f"Esperado SATURADO (≥{limiar_saturado})."
        )
        analise["acao"] = "Verificar classificar_saturacao_bairro / input N"
    elif limiar_alto <= n_ref < limiar_saturado and nivel == "ALTO":
        analise["diagnostico"] = (
            f"Cocó tem {n_ref} tradicionais e saturação ALTO está correta "
            f"(faixa {limiar_alto}–{limiar_saturado - 1})."
        )
        analise["acao"] = "Nenhuma — golden espera ALTO"
    elif n_ref < limiar_alto and nivel in ("ALTO", "SATURADO"):
        analise["diagnostico"] = (
            f"Cocó tem só {n_ref} tradicionais mas saturação {nivel} "
            f"(limiar ALTO={limiar_alto}). Possível N errado ou limiar."
        )
        analise["acao"] = "Investigar contagem gated vs nivel_saturacao"
    else:
        analise["diagnostico"] = (
            f"Cenário: {n_ref} tradicionais (coco={n_coco}, total={n_concorrentes}), "
            f"saturação {nivel}."
        )
        analise["acao"] = "Conferir limiares saturacao_bairro_*_min"

    return analise


def analisar_falha_fluxo(diag: dict) -> dict:
    """Analisa se o fluxo_score 26 é do centroide ou da via top-1."""
    fluxo = diag.get("fluxo_pedestre", {})
    top_vias = diag.get("top_vias_prospeccao", {})

    analise = {
        "fluxo_score_candidato": fluxo.get("fluxo_score_candidato") or fluxo.get("fluxo_score"),
        "fluxo_segmento": fluxo.get("fluxo_segmento"),
        "top_1_via": top_vias.get("top_1_nome"),
        "top_1_fluxo_score": top_vias.get("top_1_fluxo_score"),
        "top_1_e_arteria": top_vias.get("top_1_e_arteria"),
        "top_vias_status": top_vias.get("status"),
        "diagnostico": None,
        "acao": None,
    }

    fluxo_candidato = analise["fluxo_score_candidato"]
    top1_score = top_vias.get("top_1_fluxo_score")
    status = top_vias.get("status")

    if status not in ("ok", "ok_via_top_segments"):
        analise["diagnostico"] = (
            "top_vias_prospeccao ausente ou indisponível. "
            "Fluxo calculado apenas para candidato/centroide."
        )
        analise["acao"] = "Implementar top_vias_por_fluxo no A1 (SPEC_A1_v2 RN-A1-02)"
    elif top1_score is not None and float(top1_score) >= 70:
        analise["diagnostico"] = (
            f"Via top-1 ({top_vias.get('top_1_nome')}) tem fluxo {top1_score}, "
            f"mas fluxo_score_candidato é {fluxo_candidato}. "
            "Pipeline está calculando centroide, não via top-1."
        )
        analise["acao"] = "Corrigir pipeline para usar fluxo da via top-1, não centroide"
    elif fluxo_candidato is not None and float(fluxo_candidato) < 70:
        analise["diagnostico"] = (
            f"fluxo_score_candidato {fluxo_candidato} é provavelmente do centroide "
            f"do bairro (segmento={fluxo.get('fluxo_segmento')!r}), "
            "não da artéria estrutural."
        )
        analise["acao"] = "Verificar ponto de cálculo em build_fluxo_pedestre_block"
    else:
        analise["diagnostico"] = "Dados insuficientes para diagnóstico."
        analise["acao"] = "Coletar mais dados"

    return analise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True, help="Path do JSON fresco do pipeline")
    args = parser.parse_args()

    if not Path(args.json).exists():
        print(f"Erro: arquivo não encontrado: {args.json}")
        sys.exit(1)

    diag = diagnosticar(args.json)

    print("=" * 70)
    print("DIAGNOSTICO COCO — FALHAS DO GOLDEN CASE")
    print("=" * 70)

    print("\n-- DADOS GERAIS --")
    print(f"  Veredito: {diag['veredito']}")
    print(f"  Score bairro: {diag['score_bairro']}")
    print(f"  Nivel saturacao: {diag['nivel_saturacao']}")
    print(f"  Total concorrentes analisados: {diag['total_concorrentes_analisados']}")
    print(f"  Total concorrentes detalhados: {diag['total_concorrentes_detalhados']}")

    print("\n-- CONCORRENTES POR BAIRRO --")
    for bairro, count in sorted(
        diag.get("concorrentes_por_bairro", {}).items(),
        key=lambda x: (-x[1], str(x[0])),
    ):
        print(f"  {bairro}: {count}")

    print("\n-- DISTRIBUICAO GEOGRAFICA --")
    dist = diag.get("distribuicao_geografica")
    if dist:
        print(f"  {json.dumps(dist, ensure_ascii=False)[:500]}")
    else:
        print("  (ausente)")

    print("\n-- RENDA DO BAIRRO --")
    renda = diag.get("renda_bairro", {})
    print(f"  Renda pc: {renda.get('renda_pc')}")
    print(f"  Percentil: {renda.get('percentil')}")
    print(f"  Fonte: {renda.get('fonte')}")

    print("\n-- FLUXO RAW --")
    fp = diag.get("fluxo_pedestre") or {}
    print(f"  fluxo_score: {fp.get('fluxo_score')}")
    print(f"  fluxo_score_candidato: {fp.get('fluxo_score_candidato')}")
    print(f"  fluxo_segmento: {fp.get('fluxo_segmento')}")
    print(f"  confianca: {fp.get('confianca')}")
    print(f"  top_segments[:3]: {json.dumps(fp.get('top_segments'), ensure_ascii=False)}")

    print("\n" + "=" * 70)
    print("FALHA 1: SATURACAO")
    print("=" * 70)
    analise_sat = analisar_falha_saturacao(diag)
    print(f"  N concorrentes detalhados: {analise_sat['n_concorrentes_detalhados']}")
    print(f"  N concorrentes bairro Coco: {analise_sat['n_concorrentes_bairro_coco']}")
    print(f"  Nivel saturacao: {analise_sat['nivel_saturacao']}")
    print(f"  Diagnostico: {analise_sat['diagnostico']}")
    print(f"  Acao: {analise_sat['acao']}")

    print("\n" + "=" * 70)
    print("FALHA 2: FLUXO")
    print("=" * 70)
    analise_fluxo = analisar_falha_fluxo(diag)
    print(f"  fluxo_score_candidato: {analise_fluxo['fluxo_score_candidato']}")
    print(f"  fluxo_segmento: {analise_fluxo['fluxo_segmento']}")
    print(f"  top_vias status: {analise_fluxo['top_vias_status']}")
    print(f"  Via top-1: {analise_fluxo['top_1_via']}")
    print(f"  fluxo_score via top-1: {analise_fluxo['top_1_fluxo_score']}")
    print(f"  Via top-1 e arteria: {analise_fluxo['top_1_e_arteria']}")
    print(f"  Diagnostico: {analise_fluxo['diagnostico']}")
    print(f"  Acao: {analise_fluxo['acao']}")

    print("\n" + "=" * 70)
    print("RESUMO")
    print("=" * 70)
    print(f"  Saturacao: {analise_sat['acao']}")
    print(f"  Fluxo: {analise_fluxo['acao']}")


if __name__ == "__main__":
    main()
