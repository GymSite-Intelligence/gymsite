"""Franquias fitness — curadoria local (Fase C, sem scrape)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "franchise_curated" / "fitness_br.json"


def load_franchise_catalog() -> dict[str, Any]:
    if not DATA_PATH.is_file():
        return {"redes": []}
    try:
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"redes": []}
    except (OSError, json.JSONDecodeError):
        return {"redes": []}


def redes_por_modelo(modelo: str) -> list[dict[str, Any]]:
    modelo = (modelo or "").strip().lower()
    return [
        r
        for r in load_franchise_catalog().get("redes") or []
        if isinstance(r, dict) and (r.get("modelo") or "").lower() == modelo
    ]


def bloco_para_bundle() -> dict[str, Any]:
    cat = load_franchise_catalog()
    return {
        "fonte": cat.get("fonte", "curadoria"),
        "data_coleta": cat.get("data_coleta"),
        "redes": cat.get("redes") or [],
        "notas": cat.get("notas"),
    }
