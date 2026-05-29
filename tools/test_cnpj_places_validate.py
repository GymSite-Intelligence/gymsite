#!/usr/bin/env python3
"""Compara segmentação heurística vs Places nos entrantes (amostra)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT / "frontend" / ".env", override=False)

from tools.cnpj_fitness_tools import listar_entrantes_cnpj_fitness
from tools.cnpj_segment_classifier import classificar_segmento, segmento_label
from tools.google_maps_key import get_google_maps_api_key


def _classificar_heuristica(row: dict) -> dict:
    c = classificar_segmento(
        row.get("nome_fantasia"),
        row.get("cnae_fiscal_principal"),
        row.get("cnaes_secundarios"),
    )
    return c.to_dict()


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    cidade, uf = "Fortaleza", "CE"

    if not get_google_maps_api_key():
        print("ERRO: GOOGLE_MAPS_API_KEY não configurada no .env")
        return 1

    os.environ["CNPJ_SEGMENT_PLACES_VALIDATE"] = "0"
    sem = listar_entrantes_cnpj_fitness(
        cidade, uf, dias=90, limit=limit, validar_places=False
    )

    os.environ["CNPJ_SEGMENT_PLACES_VALIDATE"] = "1"
    com = listar_entrantes_cnpj_fitness(
        cidade, uf, dias=90, limit=limit, validar_places=True
    )

    print(f"\n=== Fortaleza — {limit} entrantes (90d) ===\n")
    print(f"{'Nome':<36} {'Heuristica':<22} {'Places':<22} {'Diff'}")
    print("-" * 95)

    mudancas = 0
    for a, b in zip(sem.get("entrantes") or [], com.get("entrantes") or []):
        h = _classificar_heuristica(a)
        seg_h = h["segmento_operacao"]
        seg_p = b.get("segmento_operacao", "")
        conf_p = b.get("segmento_confianca", "")
        met_p = b.get("segmento_metodo", "")
        nome = (a.get("nome_fantasia") or "(sem nome)")[:35]
        delta = "—" if seg_h == seg_p else "MUDOU"
        if delta == "MUDOU":
            mudancas += 1
        print(
            f"{nome:<36} {segmento_label(seg_h):<22} "
            f"{segmento_label(seg_p):<22} {delta}"
        )
        if met_p == "places" and delta == "MUDOU":
            for s in (b.get("segmento_sinais") or [])[:2]:
                print(f"    → {s}")

    print(f"\nMudanças: {mudancas}/{limit}")
    print(
        f"Pendentes (com Places): {com.get('segmentos_pendentes_validacao', '?')} | "
        f"validacao_places_ativa: {com.get('validacao_places_ativa')}"
    )
    print(
        "\nSegmentos 90d (heurística):",
        json.dumps(sem.get("novas_unidades_90d_por_segmento"), ensure_ascii=False),
    )
    print(
        "Segmentos 90d (Places):     ",
        json.dumps(com.get("novas_unidades_90d_por_segmento"), ensure_ascii=False),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
