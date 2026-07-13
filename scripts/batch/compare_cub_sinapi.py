#!/usr/bin/env python3
"""Comparativo CUB × SINAPI — relatório golden states (stdout ou markdown)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.cub_sinapi_compare import (  # noqa: E402
    compare_all,
    format_report_md,
    validate_against_golden,
)


def main() -> int:
    p = argparse.ArgumentParser(description="Comparativo golden CUB × SINAPI")
    p.add_argument("--json", action="store_true", help="Saída JSON completa")
    p.add_argument("--validate", action="store_true", help="Roda gate golden (exit 1 se falhar)")
    p.add_argument("--uf", action="append", help="Filtrar UFs (repita)")
    args = p.parse_args()

    rows = compare_all(args.uf)
    if args.validate:
        result = validate_against_golden(rows)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            if result["ok"]:
                print("OK — golden CUB×SINAPI passou")
            else:
                print("FAIL — golden CUB×SINAPI")
                for f in result["failures"]:
                    print(f"  - {f}")
        return 0 if result["ok"] else 1

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    print(format_report_md(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
