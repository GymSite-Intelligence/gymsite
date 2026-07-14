"""
CUB estadual — custo m² por UF (curadoria SindusCon/CBIC).

Proxy obra adaptação academia = CUB m² × FATOR_OBRA_ADAPTACAO (mesmo fator SINAPI).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.sinapi_indices import FATOR_OBRA_ADAPTACAO, obra_adaptacao_por_modelo

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_PATH = ROOT / "data" / "cub_pilot" / "cub_estadual_golden.json"
CACHE_PATH = ROOT / "metrics" / "cache" / "cub_estadual.json"


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def load_cub_snapshot() -> dict[str, Any] | None:
    """Cache batch tem prioridade; senão golden curado."""
    cached = _load_json(CACHE_PATH)
    if cached and cached.get("por_uf"):
        return cached
    return _load_json(GOLDEN_PATH)


def cub_indices_for_uf(uf: str) -> dict[str, Any]:
    """Bloco para market_bundle.capex_indices (régua CUB)."""
    uf = (uf or "").strip().upper()
    snap = load_cub_snapshot()
    if not snap or not snap.get("por_uf"):
        return {"uf": uf, "fonte_obra": "benchmark_fixo_fase_a", "regua": "cub"}
    block = (snap.get("por_uf") or {}).get(uf)
    if not block or block.get("cub_m2") is None:
        return {
            "uf": uf,
            "fonte_obra": "benchmark_fixo_fase_a",
            "regua": "cub",
            "aviso": f"CUB sem UF {uf} no snapshot",
        }
    cub_m2 = float(block["cub_m2"])
    obra = obra_adaptacao_por_modelo(cub_m2)
    fonte_base = snap.get("fonte") or "CUB estadual"
    fonte_uf = block.get("fonte_uf") or ""
    periodo = block.get("periodo_ref") or snap.get("periodo_ref")
    fonte_obra = fonte_base
    if fonte_uf:
        fonte_obra = f"{fonte_base} ({fonte_uf})"
    return {
        "uf": uf,
        "regua": "cub",
        "fonte_obra": fonte_obra,
        "periodo_ref": periodo,
        "cub_m2": cub_m2,
        "fator_obra_adaptacao": FATOR_OBRA_ADAPTACAO,
        "obra_adaptacao_por_m2": obra.get("mid"),
        "obra_adaptacao_por_m2_por_modelo": obra,
        "data_coleta": snap.get("data_coleta"),
    }
