#!/usr/bin/env python3
"""
Fase C — Golden gate A0 sem Deep Research.

Valida que onda red (market_waves.csv) tem bundle fresco e trilha bundle-only
funciona com A0_CONTEXT_SOURCE=ckan_bundle.

Uso:
  python scripts/batch/golden_bundle_a0_gate.py
  python scripts/batch/golden_bundle_a0_gate.py --wave red
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WAVES_CSV = ROOT / "data" / "market_waves.csv"


def _wave_rows(wave: str | None) -> list[dict[str, str]]:
    if not WAVES_CSV.is_file():
        return []
    rows: list[dict[str, str]] = []
    with WAVES_CSV.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if wave and (row.get("wave") or "").strip() != wave:
                continue
            rows.append(row)
    return rows


def main() -> int:
    p = argparse.ArgumentParser(description="Gate A0 bundle-only (Fase C)")
    p.add_argument("--wave", default="red", help="filtrar market_waves (default: red)")
    args = p.parse_args()

    os.environ["A0_CONTEXT_SOURCE"] = "ckan_bundle"

    from tools.deep_research_tool import rodar_deep_research
    from tools.enrichment_cache import reset_pipeline_enrichment_context, set_pipeline_enrichment_context
    from tools.market_bundle import (
        bundle_is_fresh,
        carregar_market_bundle,
        inject_market_bundle_context,
        load_market_bundle,
    )

    rows = _wave_rows(args.wave)
    if not rows:
        print(f"[FAIL] nenhuma linha em market_waves wave={args.wave}")
        return 1

    failures: list[str] = []
    for row in rows:
        cidade = (row.get("cidade") or "").strip()
        bairro = (row.get("bairro") or "").strip()
        uf = (row.get("uf") or "CE").strip().upper()
        label = f"{cidade}/{bairro}/{uf}"

        bundle = load_market_bundle(cidade, bairro, uf)
        if not bundle or not bundle_is_fresh(bundle):
            failures.append(f"{label}: bundle ausente ou expirado")
            continue

        md = carregar_market_bundle(cidade, bairro, uf)
        if "status=missing" in md:
            failures.append(f"{label}: carregar_market_bundle missing")
            continue

        ctx = inject_market_bundle_context(cidade, bairro, uf, {})
        if not ctx.get("market_bundle_available"):
            failures.append(f"{label}: inject falhou")
            continue

        token = set_pipeline_enrichment_context({**ctx, "skip_deep_research": True})
        try:
            t0 = time.perf_counter()
            out = rodar_deep_research(cidade, bairro)
            elapsed = time.perf_counter() - t0
        finally:
            reset_pipeline_enrichment_context(token)

        if elapsed > 5.0:
            failures.append(f"{label}: DR path lento ({elapsed:.1f}s) — possível chamada real")
        if "market_bundle" not in out and "Briefing de mercado" not in out:
            failures.append(f"{label}: skip DR sem conteúdo bundle")

        stale = bundle.get("stale", False)
        print(
            f"[OK] {label} stale={stale} missing={len(bundle.get('missing_fields') or [])} "
            f"dr_skip={elapsed:.2f}s"
        )

    if failures:
        for f in failures:
            print(f"[FAIL] {f}")
        return 1

    print(f"\n=== GOLDEN BUNDLE A0 GATE PASS ({len(rows)} locais, wave={args.wave}) ===\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
