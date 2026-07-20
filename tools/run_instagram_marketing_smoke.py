#!/usr/bin/env python3
"""Smoke test live — Instagram marketing (requer SEARCHAPI_KEY no .env)."""
from __future__ import annotations

import json
import sys

from dotenv import load_dotenv

load_dotenv()


def main() -> int:
    from tools.instagram_marketing import (
        analisar_concorrentes_com_reviews,
        buscar_candidatos_ig_obra,
    )

    cidade, uf, bairro = "Fortaleza", "CE", "Cocó"
    if len(sys.argv) >= 4:
        cidade, uf, bairro = sys.argv[1], sys.argv[2], sys.argv[3]

    print("=== Concorrentes com reviews → IG + posts ===")
    rev = analisar_concorrentes_com_reviews(
        cidade=cidade, uf=uf, bairro=bairro, max_concorrentes=4,
    )
    print(json.dumps({
        "status": rev.get("status"),
        "concorrentes_com_reviews": rev.get("concorrentes_com_reviews"),
        "perfis_ig_ok": rev.get("perfis_ig_ok"),
        "carimbo": rev.get("carimbo"),
        "resumo": [
            {
                "nome": p.get("nome"),
                "status": p.get("status"),
                "username": p.get("username"),
                "fonte": (p.get("descoberta") or {}).get("fonte_descoberta"),
                "tema_campeao": (p.get("diagnostico") or {}).get("tema_campeao_engajamento"),
            }
            for p in (rev.get("perfis_ig") or [])
        ],
    }, ensure_ascii=False, indent=2))

    print("\n=== Busca IG obra/pré-abertura (independente) ===")
    obra = buscar_candidatos_ig_obra(
        cidade=cidade, uf=uf, bairro=bairro, max_perfis=3,
    )
    print(json.dumps({
        "status": obra.get("status"),
        "candidatos_links": obra.get("candidatos_links"),
        "carimbo": obra.get("carimbo"),
        "perfis": [
            {
                "username": p.get("username"),
                "status": p.get("status"),
                "followers": p.get("followers"),
                "tem_metodologia_obra": p.get("tem_metodologia_obra"),
                "tema_campeao": p.get("tema_campeao"),
            }
            for p in (obra.get("perfis") or [])
        ],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
