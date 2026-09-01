"""
tests/investiga_cobertura_coco.py

Investigacao da Falha 1 — funil de concorrentes Cocó.
Rastreia onde a contagem cai: A3a (coleta) -> A3b (filtro) -> A6 (saturacao).

Uso:
    python tests/investiga_cobertura_coco.py --json metrics/relatorios/rpt_1786376018.json
    python tests/investiga_cobertura_coco.py --json metrics/relatorios/rpt_1786376018.json --comparar metrics/relatorios/rpt_1781804284.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Referencial Cocó — academia TRADICIONAL gated (não Aggregate amplo ~37/1km).
# Limiares: ≥6 ALTO, ≥10 SATURADO (parametros_metodologia).
GOLDEN_HISTORICO = {
    "concorrentes_bairro_tradicionais_min": 6,
    "concorrentes_bairro_tradicionais_max_alto": 9,
    "concorrentes_raio_3km_contexto": 211,  # panorama amplo — contexto, não saturação
    "saturacao_esperada": "ALTO",
}


def _carregar(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _lista_dicts(val) -> list[dict]:
    if isinstance(val, list):
        return [c for c in val if isinstance(c, dict)]
    if isinstance(val, dict):
        for k in ("candidatos", "concorrentes", "academias", "items", "results"):
            inner = val.get(k)
            if isinstance(inner, list):
                return [c for c in inner if isinstance(c, dict)]
    return []


def _extrair_candidatos(data: dict) -> list[dict]:
    """Extrai lista de concorrentes de varias fontes possiveis."""
    if not isinstance(data, dict):
        return []

    # Envelope dedicado
    for chave in ("concorrentes_brutos", "concorrentes_detalhados", "inteligencia_competitiva"):
        bloco = data.get(chave)
        if bloco is None:
            continue
        cand = _lista_dicts(bloco)
        if cand:
            return cand
        if isinstance(bloco, dict):
            for sub in ("concorrentes_detalhados", "academias_analisadas", "competitors_set"):
                cand = _lista_dicts(bloco.get(sub))
                if cand:
                    return cand

    # output_consolidado (JSON local tipico)
    out = data.get("output_consolidado") or {}
    if isinstance(out, dict):
        for chave in (
            "academias_analisadas",
            "competitors_set",
            "concorrentes_detalhados",
            "concorrentes_brutos",
        ):
            cand = _lista_dicts(out.get(chave))
            if cand:
                return cand

    # Fallbacks no root
    for chave in ("academias_analisadas", "competitors_set"):
        cand = _lista_dicts(data.get(chave))
        if cand:
            return cand

    return []


def _extrair_brutos(data: dict) -> list[dict]:
    """Prefer brutos; se ausente, tenta lista mais ampla no consolidado."""
    root = data.get("concorrentes_brutos")
    cand = _lista_dicts(root) if root is not None else []
    if cand:
        return cand

    out = data.get("output_consolidado") or {}
    if isinstance(out, dict):
        # academias_analisadas costuma ser o conjunto pos-coleta (pre/pos filtro)
        for chave in ("academias_analisadas", "concorrentes_brutos", "competitors_set"):
            cand = _lista_dicts(out.get(chave))
            if cand:
                return cand
    return _extrair_candidatos(data)


def _extrair_detalhados(data: dict) -> list[dict]:
    intelig = data.get("inteligencia_competitiva")
    if intelig is not None:
        cand = _lista_dicts(intelig)
        if cand:
            return cand
        if isinstance(intelig, dict):
            for sub in ("concorrentes_detalhados", "academias_analisadas"):
                cand = _lista_dicts(intelig.get(sub))
                if cand:
                    return cand

    out = data.get("output_consolidado") or {}
    if isinstance(out, dict):
        # competitors_set / amostra aprofundada = tipico pos-A3b
        for chave in ("competitors_set", "concorrentes_detalhados"):
            cand = _lista_dicts(out.get(chave))
            if cand:
                return cand
        # se so ha academias_analisadas, usa como detalhados tambem
        cand = _lista_dicts(out.get("academias_analisadas"))
        if cand:
            return cand

    return _extrair_candidatos(data)


def _contar_por_bairro(concorrentes: list[dict]) -> dict[str, int]:
    contagem: dict[str, int] = {}
    for c in concorrentes:
        bairro = (
            c.get("bairro_concorrente")
            or c.get("bairro")
            or c.get("bairro_normalizado")
            or "desconhecido"
        )
        bairro = str(bairro).strip()
        contagem[bairro] = contagem.get(bairro, 0) + 1
    return contagem


def _contar_coco(contagem: dict[str, int]) -> int:
    """Soma concorrentes cujo bairro contem 'coco' (frouxo)."""
    total = 0
    for bairro, n in contagem.items():
        if "coco" in bairro.lower().replace("ó", "o").replace("Ó", "o"):
            total += n
    return total


def investigar(json_path: str, comparar_path: str | None = None) -> dict:
    data = _carregar(json_path)
    out = data.get("output_consolidado", {}) if isinstance(data, dict) else {}

    # ── ETAPA 1: funil A3a -> A3b ───────────────────────────────────────
    brutos = _extrair_brutos(data)
    detalhados = _extrair_detalhados(data)

    contagem_brutos = _contar_por_bairro(brutos)
    contagem_detalhados = _contar_por_bairro(detalhados)

    n_coco_brutos = _contar_coco(contagem_brutos)
    n_coco_detalhados = _contar_coco(contagem_detalhados)

    # ── ETAPA 2: filtro A3b — quem foi removido ─────────────────────────
    removidos = []
    if n_coco_brutos > n_coco_detalhados:
        nomes_detalhados = {
            str(c.get("nome") or c.get("name") or c.get("titulo") or "").lower()
            for c in detalhados
        }
        for c in brutos:
            bairro = (
                str(c.get("bairro_concorrente") or c.get("bairro") or "")
                .lower()
                .replace("ó", "o")
            )
            nome = str(c.get("nome") or c.get("name") or c.get("titulo") or "")
            if "coco" in bairro and nome.lower() not in nomes_detalhados:
                removidos.append(
                    {
                        "nome": nome,
                        "bairro": bairro,
                        "business_status": c.get("business_status"),
                        "motivo_suspeito": c.get("business_status", "OPERATIONAL"),
                    }
                )

    # ── ETAPA 3: saturação — bairro vs raio ─────────────────────────────
    nivel = out.get("nivel_saturacao")
    total_analisados = out.get("total_concorrentes_analisados")
    panorama = out.get("panorama_competitivo") or {}
    cross_check = (
        out.get("cross_check")
        or out.get("total_concorrentes_bairro")
        or panorama.get("total_encontrados_raio")
        or panorama.get("nivel_saturacao")
    )

    # ── ETAPA 4: metadata de coleta (MAX_ENRIQUECIMENTO) ────────────────
    envelope_brutos = data.get("concorrentes_brutos") or {}
    metadata_coleta = {}
    if isinstance(envelope_brutos, dict):
        metadata_coleta = envelope_brutos.get("metadata") or envelope_brutos.get("_meta") or {}
    meta_exec = data.get("metadata_execucao") or {}
    if isinstance(meta_exec, dict) and not metadata_coleta:
        # pistas de limite de enriquecimento
        metadata_coleta = {
            k: meta_exec[k]
            for k in meta_exec
            if any(
                tok in str(k).lower()
                for tok in ("enrich", "enriquec", "max_", "a3a", "competidor", "satur")
            )
        }
        if not metadata_coleta and meta_exec:
            # amostra curta das chaves disponiveis
            metadata_coleta = {"_chaves_metadata_execucao": list(meta_exec.keys())[:40]}

    # Sinais extras do consolidado / panorama
    sinais = {
        "nivel_saturacao_out": nivel,
        "nivel_saturacao_panorama": panorama.get("nivel_saturacao") if isinstance(panorama, dict) else None,
        "nivel_saturacao_amostra": panorama.get("nivel_saturacao_amostra") if isinstance(panorama, dict) else None,
        "total_encontrados_raio": panorama.get("total_encontrados_raio") if isinstance(panorama, dict) else None,
        "total_concorrentes_analisados_panorama": (
            panorama.get("total_concorrentes_analisados") if isinstance(panorama, dict) else None
        ),
        "metodologia": panorama.get("metodologia") if isinstance(panorama, dict) else None,
        "len_academias_analisadas": len(_lista_dicts(out.get("academias_analisadas"))),
        "len_competitors_set": len(_lista_dicts(out.get("competitors_set"))),
        "tem_concorrentes_brutos_root": "concorrentes_brutos" in data,
        "tem_inteligencia_competitiva_root": "inteligencia_competitiva" in data,
    }

    # ── ETAPA 5: comparação histórica (se fornecida) ────────────────────
    comparacao = None
    if comparar_path and Path(comparar_path).exists():
        hist = _carregar(comparar_path)
        hist_brutos = _extrair_brutos(hist)
        hist_detalhados = _extrair_detalhados(hist)
        hist_out = hist.get("output_consolidado") or {}
        comparacao = {
            "arquivo": comparar_path,
            "n_brutos": len(hist_brutos),
            "n_detalhados": len(hist_detalhados),
            "n_coco_brutos": _contar_coco(_contar_por_bairro(hist_brutos)),
            "n_coco_detalhados": _contar_coco(_contar_por_bairro(hist_detalhados)),
            "nivel_saturacao": hist_out.get("nivel_saturacao") if isinstance(hist_out, dict) else None,
        }

    return {
        "funil": {
            "n_brutos": len(brutos),
            "n_detalhados": len(detalhados),
            "n_coco_brutos": n_coco_brutos,
            "n_coco_detalhados": n_coco_detalhados,
            "perda_no_filtro": len(brutos) - len(detalhados),
            "perda_coco_no_filtro": n_coco_brutos - n_coco_detalhados,
        },
        "contagem_brutos_por_bairro": contagem_brutos,
        "contagem_detalhados_por_bairro": contagem_detalhados,
        "removidos_do_coco": removidos,
        "saturacao": {
            "nivel": nivel,
            "total_analisados": total_analisados,
            "cross_check": cross_check,
        },
        "metadata_coleta": metadata_coleta,
        "sinais": sinais,
        "comparacao_historica": comparacao,
    }


def decidir_hipotese(inv: dict) -> dict:
    """Aplica a regra de decisão pós-investigação (tradicionais + limiares 6/10)."""
    funil = inv["funil"]
    n_brutos = funil["n_brutos"]
    n_detalhados = funil["n_detalhados"]
    n_coco_brutos = funil["n_coco_brutos"]
    n_coco_detalhados = funil["n_coco_detalhados"]
    n_min = GOLDEN_HISTORICO["concorrentes_bairro_tradicionais_min"]
    n_max_alto = GOLDEN_HISTORICO["concorrentes_bairro_tradicionais_max_alto"]
    sat_esp = GOLDEN_HISTORICO["saturacao_esperada"]
    sinais = inv.get("sinais") or {}

    decisao: dict[str, str | None] = {"hipotese": None, "evidencia": None, "acao": None}

    len_set = sinais.get("len_competitors_set") or 0
    len_acad = sinais.get("len_academias_analisadas") or 0
    n_ref = n_brutos  # proxy tradicionais pos-coleta no consolidado

    if n_ref < n_min:
        decisao["hipotese"] = "H1"
        evidencia = (
            f"Coleta abaixo da faixa ALTO: N={n_ref} < min {n_min} tradicionais."
        )
        acao = (
            "Investigar recall A3a (Formato 1 + gate tipo). "
            "Nao usar Aggregate amplo (~37) como meta."
        )
        if len_set and len_set <= 3:
            decisao["hipotese"] = "H1+H3"
            evidencia += (
                f" competitors_set={len_set} (teto enriquecimento); "
                f"academias_analisadas={len_acad}."
            )
        decisao["evidencia"] = evidencia
        decisao["acao"] = acao
    elif n_min <= n_ref <= n_max_alto:
        nivel = (inv.get("saturacao") or {}).get("nivel")
        if nivel and str(nivel).upper() == sat_esp:
            decisao["hipotese"] = "OK"
            decisao["evidencia"] = (
                f"N={n_ref} na faixa ALTO ({n_min}-{n_max_alto}) e saturacao={nivel}."
            )
            decisao["acao"] = "Nenhuma — alinhado ao golden tradicional."
        else:
            decisao["hipotese"] = "H4"
            decisao["evidencia"] = (
                f"N={n_ref} ok para ALTO, mas saturacao={nivel!r} "
                f"(esperado {sat_esp})."
            )
            decisao["acao"] = "Verificar classificar_saturacao_bairro / input N."
    elif n_ref >= 10:
        nivel = (inv.get("saturacao") or {}).get("nivel")
        if str(nivel or "").upper() != "SATURADO":
            decisao["hipotese"] = "H4"
            decisao["evidencia"] = (
                f"N={n_ref} ≥10 mas saturacao={nivel!r} (esperado SATURADO)."
            )
            decisao["acao"] = "Calibrar ou corrigir input de classificar_saturacao_bairro."
        else:
            decisao["hipotese"] = "OK"
            decisao["evidencia"] = f"N={n_ref} SATURADO coerente."
            decisao["acao"] = "Atualizar golden saturacao_esperada para SATURADO se persistir."
    else:
        decisao["hipotese"] = "INCONCLUSIVO"
        decisao["evidencia"] = (
            f"brutos={n_brutos}, detalhados={n_detalhados}, "
            f"coco_brutos={n_coco_brutos}, coco_detalhados={n_coco_detalhados}."
        )
        decisao["acao"] = "Coletar mais dados ou rodar comparacao historica (--comparar)."

    return decisao


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True, help="JSON fresco do pipeline")
    parser.add_argument("--comparar", help="JSON historico para comparacao (opcional)")
    parser.add_argument("--salvar", help="Path para salvar o relatorio (opcional)")
    args = parser.parse_args()

    if not Path(args.json).exists():
        print(f"Erro: arquivo nao encontrado: {args.json}")
        sys.exit(1)

    inv = investigar(args.json, args.comparar)
    decisao = decidir_hipotese(inv)

    print("=" * 70)
    print("INVESTIGACAO COBERTURA COCO — FALHA 1 (SATURACAO)")
    print("=" * 70)

    print("\n-- ETAPA 1: FUNIL A3a -> A3b --")
    f = inv["funil"]
    print(f"  Brutos (A3a):         {f['n_brutos']}")
    print(f"  Detalhados (A3b):     {f['n_detalhados']}")
    print(f"  Perda no filtro:      {f['perda_no_filtro']}")
    print(f"  No Coco (brutos):     {f['n_coco_brutos']}")
    print(f"  No Coco (detalhados): {f['n_coco_detalhados']}")

    print("\n-- CONTAGEM BRUTOS POR BAIRRO --")
    for bairro, n in sorted(
        inv.get("contagem_brutos_por_bairro", {}).items(),
        key=lambda x: (-x[1], str(x[0])),
    ):
        print(f"  {bairro}: {n}")

    print("\n-- ETAPA 2: REMOVIDOS DO COCO NO FILTRO --")
    if inv["removidos_do_coco"]:
        for r in inv["removidos_do_coco"][:10]:
            print(f"  - {r['nome']} (status: {r['business_status']})")
    else:
        print("  (nenhum removido ou dados insuficientes)")

    print("\n-- ETAPA 3: SATURACAO --")
    s = inv["saturacao"]
    print(f"  Nivel:                {s['nivel']}")
    print(f"  Total analisados:     {s['total_analisados']}")
    print(f"  Cross-check:          {s['cross_check']}")
    sinais = inv.get("sinais") or {}
    print(f"  Panorama nivel:       {sinais.get('nivel_saturacao_panorama')}")
    print(f"  Panorama amostra:     {sinais.get('nivel_saturacao_amostra')}")
    print(f"  Total raio:           {sinais.get('total_encontrados_raio')}")
    print(f"  academias_analisadas: {sinais.get('len_academias_analisadas')}")
    print(f"  competitors_set:      {sinais.get('len_competitors_set')}")
    print(f"  tem concorrentes_brutos root: {sinais.get('tem_concorrentes_brutos_root')}")
    print(f"  tem inteligencia root:        {sinais.get('tem_inteligencia_competitiva_root')}")
    if sinais.get("metodologia"):
        print(f"  Metodologia: {sinais.get('metodologia')}")

    print("\n-- ETAPA 4: METADATA DE COLETA --")
    if inv["metadata_coleta"]:
        print(f"  {json.dumps(inv['metadata_coleta'], ensure_ascii=False)[:800]}")
    else:
        print("  (ausente — nao e possivel verificar MAX_ENRIQUECIMENTO)")

    print("\n-- ETAPA 5: COMPARACAO HISTORICA --")
    if inv["comparacao_historica"]:
        c = inv["comparacao_historica"]
        print(f"  Arquivo: {c['arquivo']}")
        print(f"  Brutos historicos:      {c['n_brutos']}")
        print(f"  Detalhados historicos:  {c['n_detalhados']}")
        print(f"  No Coco (historico):    {c['n_coco_brutos']}")
        print(f"  Saturacao historica:    {c['nivel_saturacao']}")
    else:
        print("  (nao fornecida — use --comparar para comparar com run historico)")

    print("\n" + "=" * 70)
    print("DECISAO")
    print("=" * 70)
    print(f"  Hipotese:  {decisao['hipotese']}")
    print(f"  Evidencia: {decisao['evidencia']}")
    print(f"  Acao:      {decisao['acao']}")

    if args.salvar:
        relatorio = {"investigacao": inv, "decisao": decisao}
        Path(args.salvar).write_text(
            json.dumps(relatorio, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"\nRelatorio salvo em: {args.salvar}")


if __name__ == "__main__":
    main()
