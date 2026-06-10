"""
Renda e população por bairro — Fase B.

1. Piloto curado em data/bairro_renda_pilot/{cidade}_{uf}.json
2. Futuro: CKAN DataStore municipal (discover_ckan_catalog)
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PILOT_DIR = ROOT / "data" / "bairro_renda_pilot"


def _norm(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", (s or "").strip().lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _pilot_path(cidade: str, uf: str) -> Path:
    slug = f"{_norm(cidade)}_{uf.strip().lower()}"
    return PILOT_DIR / f"{slug}.json"


def load_pilot_catalog(cidade: str, uf: str) -> dict[str, Any] | None:
    path = _pilot_path(cidade, uf)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def enrich_demografia_bairro(
    demografia: dict[str, Any],
    cidade: str,
    bairro: str,
    uf: str,
) -> dict[str, Any]:
    """
    Preenche demografia['bairro'] quando há entrada no piloto curado.
    """
    out = dict(demografia)
    bairro_block = dict(out.get("bairro") or {})
    bairro_block.setdefault("granularidade", "bairro")

    if not (bairro or "").strip():
        out["bairro"] = bairro_block
        return out

    pilot = load_pilot_catalog(cidade, uf)
    if not pilot:
        out["bairro"] = bairro_block
        return out

    entry = (pilot.get("bairros") or {}).get(_norm(bairro))
    if not entry:
        out["bairro"] = bairro_block
        return out

    bairro_block["renda_media"] = entry.get("renda_media")
    bairro_block["populacao"] = entry.get("populacao")
    bairro_block["fonte"] = pilot.get("fonte", "bairro_renda_pilot")
    bairro_block["dataset_id"] = entry.get("dataset_id")
    bairro_block["data_referencia"] = pilot.get("data_referencia")
    bairro_block["nota"] = pilot.get("nota")
    out["bairro"] = bairro_block
    return out
