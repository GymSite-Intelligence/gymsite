#!/usr/bin/env python3
"""Aggregate gym points to H3 res=8 JSON for CARTO import / GymSite lookup."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

H3_RES = 8


def points_to_rows(points: list[dict], *, fonte: str) -> dict:
    import h3

    counts: Counter[str] = Counter()
    cidade_by_cell: dict[str, str] = {}
    for p in points:
        lat = float(p["lat"])
        lng = float(p["lng"])
        cidade = str(p.get("cidade") or "desconhecida").strip()
        cell = h3.latlng_to_cell(lat, lng, H3_RES)
        counts[cell] += 1
        if cell not in cidade_by_cell:
            cidade_by_cell[cell] = cidade
    gerado = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    rows = [
        {"hex": hx, "n_academias": n, "cidade": cidade_by_cell[hx]}
        for hx, n in sorted(counts.items())
    ]
    return {"h3_res": H3_RES, "fonte": fonte, "gerado_em": gerado, "rows": rows}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True, help="JSON array of points")
    p.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "carto" / "gym_hex_cidade.json",
    )
    p.add_argument("--fonte", default="gym_hex_cidade")
    args = p.parse_args()
    points = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(points, list):
        raise SystemExit("input must be a JSON array")
    payload = points_to_rows(points, fonte=args.fonte)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.output} rows={len(payload['rows'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
