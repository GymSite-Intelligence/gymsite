"""Taxas municipais / CAU — piloto curado (Fase C)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PILOT_DIR = ROOT / "data" / "legal_fees_pilot"


def _slug(cidade: str, uf: str) -> str:
    c = re.sub(r"[^a-z0-9]+", "_", (cidade or "").lower()).strip("_")
    return f"{c}_{(uf or '').lower()}"


def load_legal_fees(cidade: str, uf: str) -> dict[str, Any] | None:
    path = PILOT_DIR / f"{_slug(cidade, uf)}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def bloco_para_bundle(cidade: str, uf: str) -> dict[str, Any]:
    data = load_legal_fees(cidade, uf)
    if not data:
        return {
            "disponivel": False,
            "cidade": cidade,
            "uf": uf.upper(),
            "fonte": None,
        }
    return {
        "disponivel": True,
        "cidade": data.get("cidade", cidade),
        "uf": data.get("uf", uf.upper()),
        "fonte": data.get("fonte"),
        "data_coleta": data.get("data_coleta"),
        "taxas": data.get("taxas") or {},
        "prazo_meses_tipico": data.get("prazo_meses_tipico") or {},
        "notas": data.get("notas"),
    }
