#!/usr/bin/env python3
"""Gera JSONs legal_fees_pilot v1 (13 cidades novas) + manifest 15."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PILOT_DIR = ROOT / "data" / "legal_fees_pilot"

# Multiplicadores vs baseline Curitiba (alvará 595.78, bombeiros 1800, sanit 1215.63, r_m2 120).
NEW_CITIES: dict[tuple[str, str], tuple[float, float, float, float, int, int]] = {
    ("São Paulo", "SP"): (1.40, 1.30, 1.20, 130, 20000, 250000),
    ("Rio de Janeiro", "RJ"): (1.30, 1.40, 1.10, 125, 18000, 220000),
    ("Belo Horizonte", "MG"): (0.90, 1.00, 1.00, 110, 16000, 180000),
    ("Brasília", "DF"): (1.10, 1.20, 1.00, 115, 17000, 190000),
    ("Salvador", "BA"): (0.85, 0.90, 0.95, 95, 14000, 170000),
    ("Recife", "PE"): (0.80, 0.85, 0.90, 95, 14000, 165000),
    ("Porto Alegre", "RS"): (1.00, 1.10, 1.05, 115, 17000, 195000),
    ("Goiânia", "GO"): (0.75, 0.80, 0.85, 90, 13000, 160000),
    ("Florianópolis", "SC"): (1.05, 1.00, 1.00, 110, 16000, 185000),
    ("Campinas", "SP"): (1.00, 1.00, 1.00, 105, 15000, 175000),
    ("Niterói", "RJ"): (1.20, 1.30, 1.10, 120, 17000, 200000),
    ("Manaus", "AM"): (0.70, 0.75, 0.80, 85, 12000, 150000),
    ("Belém", "PA"): (0.65, 0.70, 0.75, 80, 12000, 145000),
}

BASE_ALV = 595.78
BASE_BOM = 1800.0
BASE_SAN = 1215.63


def _faixa(typ: float, spread: float = 0.45) -> dict[str, float]:
    lo = round(max(typ * (1 - spread), 0), 2)
    hi = round(typ * (1 + spread), 2)
    return {"min": lo, "max": hi, "typico": round(typ, 2)}


def _block(cidade: str, uf: str, mults: tuple[float, float, float, float, int, int]) -> dict:
    ma, mb, ms, rm2, pmin, pmax = mults
    return {
        "cidade": cidade,
        "uf": uf,
        "fonte": "curadoria_gymsite_v1 — faixa conservadora por capital; revalidar prefeitura/CBM",
        "data_coleta": "2026-07-13",
        "revisao_pendente": True,
        "notas": "Estimativa piloto v1 para A4 — typico calibrado vs Curitiba; não substitui tabela municipal.",
        "taxas": {
            "alvara_funcionamento_brl": _faixa(BASE_ALV * ma, 0.35),
            "taxa_bombeiros_brl": _faixa(BASE_BOM * mb, 0.55),
            "projeto_arquitetonico_cau_brl": {
                "min": pmin,
                "max": pmax,
                "r_m2": {"min": round(rm2 * 0.65, 0), "max": round(rm2 * 1.45, 0), "typico": rm2},
            },
            "vistoria_sanitaria_brl": _faixa(BASE_SAN * ms, 0.50),
        },
        "prazo_meses_tipico": {"alvara": 4, "bombeiros": 2},
    }


def main() -> None:
    from tools.legal_fees_loader import PILOT_CITIES, _slug

    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_rows = []
    for cidade, uf in PILOT_CITIES:
        slug = _slug(cidade, uf)
        manifest_rows.append({"cidade": cidade, "uf": uf, "slug": slug})
        key = (cidade, uf)
        if key in NEW_CITIES:
            path = PILOT_DIR / f"{slug}.json"
            path.write_text(
                json.dumps(_block(cidade, uf, NEW_CITIES[key]), ensure_ascii=False, indent=2)
                + "\n",
                encoding="utf-8",
            )
            print(f"Wrote {path.name}")

    manifest = {
        "version": "1.0",
        "data_coleta": "2026-07-13",
        "notas": "15 praças piloto legal_fees. Fortaleza/Curitiba curadas; demais revisao_pendente.",
        "cidades": manifest_rows,
    }
    (PILOT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Wrote manifest.json")


if __name__ == "__main__":
    main()
