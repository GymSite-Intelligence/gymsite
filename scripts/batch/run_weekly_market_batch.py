#!/usr/bin/env python3
"""
Batch semanal — CVM + SINAPI + benchmarks + market bundles (ondas em market_waves.csv).

Uso:
  python scripts/batch/run_weekly_market_batch.py
  python scripts/batch/run_weekly_market_batch.py --skip-enrichment
  python scripts/batch/run_weekly_market_batch.py --only-cvm

Cron VM (domingo 03:00):
  0 3 * * 0 cd /opt/gymsite_intelligence && python scripts/batch/run_weekly_market_batch.py >> /var/log/gym_market_batch.log 2>&1
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WAVES_CSV = ROOT / "data" / "market_waves.csv"


def _run(args: list[str], *, label: str) -> int:
    cmd = [sys.executable, *args]
    print(f"\n>>> {label}")
    print(">", " ".join(cmd))
    rc = subprocess.call(cmd, cwd=str(ROOT))
    if rc != 0:
        print(f"[FAIL] {label} exit={rc}")
    else:
        print(f"[OK] {label}")
    return rc


def _wave_locations() -> list[tuple[str, str, str]]:
    if not WAVES_CSV.is_file():
        return [("Fortaleza", "Meireles", "CE")]
    seen: set[tuple[str, str, str]] = set()
    out: list[tuple[str, str, str]] = []
    with WAVES_CSV.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            cidade = (row.get("cidade") or "").strip()
            bairro = (row.get("bairro") or "").strip()
            uf = (row.get("uf") or "CE").strip().upper()
            if not cidade:
                continue
            key = (cidade, bairro, uf)
            if key in seen:
                continue
            seen.add(key)
            out.append(key)
    return out or [("Fortaleza", "Meireles", "CE")]


def main() -> int:
    p = argparse.ArgumentParser(description="Batch semanal market data")
    p.add_argument("--skip-cvm", action="store_true")
    p.add_argument("--skip-sinapi", action="store_true")
    p.add_argument("--skip-benchmarks", action="store_true")
    p.add_argument("--skip-bundles", action="store_true")
    p.add_argument(
        "--skip-enrichment",
        action="store_true",
        help="bundles usam cache enrichment existente (mais rápido)",
    )
    p.add_argument("--only-cvm", action="store_true", help="só CVM + benchmarks")
    args = p.parse_args()

    if args.only_cvm:
        args.skip_sinapi = True
        args.skip_bundles = True

    steps: list[tuple[str, list[str]]] = []

    if not args.skip_cvm:
        steps.append(
            (
                "CVM SMFT3",
                ["scripts/batch/update_benchmark_snapshots.py", "--fetch-cvm"],
            )
        )
    if not args.skip_sinapi:
        steps.append(("SINAPI/SIDRA", ["scripts/batch/update_capex_indices.py"]))
    if not args.skip_benchmarks:
        steps.append(
            (
                "benchmark_snapshots",
                ["scripts/batch/update_benchmark_snapshots.py", "--skip-cvm"],
            )
        )

    rc = 0
    for label, script_args in steps:
        if _run(script_args, label=label) != 0:
            rc = 1

    if not args.skip_bundles:
        for cidade, bairro, uf in _wave_locations():
            bundle_args = [
                "scripts/batch/build_market_bundles.py",
                "--cidade",
                cidade,
                "--bairro",
                bairro,
                "--uf",
                uf,
                "--skip-ckan",
            ]
            if args.skip_enrichment:
                pass  # default: usa cache se fresco
            else:
                bundle_args.append("--refresh-enrichment")
            label = f"bundle {cidade}/{bairro or '-'}/{uf}"
            # Non-zero includes GeocodeBairroError → main() exit 2 (hard gate).
            if _run(bundle_args, label=label) != 0:
                rc = 1

    if rc == 0 and not args.skip_bundles:
        gate_args = ["scripts/batch/golden_bundle_a0_gate.py", "--wave", "red"]
        if _run(gate_args, label="golden_bundle_a0_gate (Fase C)") != 0:
            rc = 1

    if rc == 0:
        print("\n=== WEEKLY BATCH OK ===\n")
    else:
        print("\n=== WEEKLY BATCH COM FALHAS ===\n")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
