#!/usr/bin/env python3
"""CLI do E2E gate (mesmo que tools/test_e2e_market_pipeline.py)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    p = argparse.ArgumentParser(description="E2E market pipeline gate")
    p.add_argument("--stage", default="a6_e2e", help="etapa para escopo E2E (a1..a6)")
    p.add_argument("--rebuild-bundle", action="store_true")
    args = p.parse_args()

    from scripts.batch.e2e_gate import run_e2e_for_stage

    return run_e2e_for_stage(args.stage, rebuild_bundle=args.rebuild_bundle)


if __name__ == "__main__":
    raise SystemExit(main())
