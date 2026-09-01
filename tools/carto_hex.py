from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import h3

H3_RES = 8
DEFAULT_TABLE = Path(__file__).resolve().parents[1] / "data" / "carto" / "gym_hex_cidade.json"
BASE_STAMP = "H3 res 8 da tabela gym_hex_cidade"


class HexCountNotFound(Exception):
    pass


def load_hex_table(path: Path | None = None) -> dict[str, Any]:
    raw = path or Path(os.getenv("CARTO_HEX_TABLE_PATH", str(DEFAULT_TABLE)))
    data = json.loads(raw.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("rows"), list):
        raise ValueError("hex table invalid")
    return data


def lookup_hex_count(lat: float, lng: float, table: dict[str, Any]) -> dict[str, Any]:
    cell = h3.latlng_to_cell(float(lat), float(lng), H3_RES)
    for row in table["rows"]:
        if str(row.get("hex")) == cell:
            n = int(row["n_academias"])
            return {
                "n_academias": n,
                "hex": cell,
                "cidade": str(row.get("cidade") or ""),
                "fonte": str(table.get("fonte") or "gym_hex_cidade"),
                "gerado_em": str(table.get("gerado_em") or ""),
                "base": BASE_STAMP,
            }
    raise HexCountNotFound(cell)
