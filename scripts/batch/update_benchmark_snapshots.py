#!/usr/bin/env python3
"""
Atualiza metrics/cache/benchmark_snapshots.json (setorial + sector_listed).

Hierarquia: snapshot disco → (opcional) grounding → defaults ACAD.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SNAPSHOT_PATH = ROOT / "metrics" / "cache" / "benchmark_snapshots.json"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--force-grounding", action="store_true", help="Força Search Grounding (rede)")
    p.add_argument(
        "--fetch-cvm",
        action="store_true",
        help="Baixa ITR CVM para SMFT3 e grava sector_listed.json (rede)",
    )
    p.add_argument("--skip-cvm", action="store_true", help="Não atualiza sector_listed via CVM")
    args = p.parse_args()

    from tools.benchmarks_tool import DEFAULTS_FALLBACK, obter_benchmarks_setoriais
    from tools.cvm_listed_metrics import obter_sector_listed

    if args.fetch_cvm:
        from tools.cvm_fetch import atualizar_sector_listed_via_cvm

        sector = atualizar_sector_listed_via_cvm()
        print("cvm fetch: empresas=", len(sector.get("empresas") or []))
        smft = next(
            (e for e in sector.get("empresas") or [] if e.get("ticker") == "SMFT3"),
            None,
        )
        if smft:
            print("SMFT3 periodo:", smft.get("periodo_ref"), "margem:", (smft.get("kpis") or {}).get("margem_ebitda_pct"))
    elif not args.skip_cvm:
        from tools.cvm_listed_metrics import save_sector_listed_snapshot

        sector = obter_sector_listed()
        save_sector_listed_snapshot(sector)
    else:
        sector = obter_sector_listed()

    if args.force_grounding:
        setorial = obter_benchmarks_setoriais(force_refresh=True)
    else:
        setorial = obter_benchmarks_setoriais(force_refresh=False)
        if setorial.get("fonte", "").startswith("fallback"):
            setorial = {**DEFAULTS_FALLBACK, **setorial}

    payload = {
        "version": "1.0",
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "setorial": setorial,
        "sector_listed": sector,
    }
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("written:", SNAPSHOT_PATH)
    try:
        from tools.market_store import supabase_enabled, upsert_snapshot

        if supabase_enabled() and upsert_snapshot("benchmark_snapshots", payload):
            print("supabase: market_snapshots.benchmark_snapshots atualizado")
    except Exception as e:
        print(f"supabase snapshot push falhou: {type(e).__name__}: {e}")
    print("setorial fonte:", setorial.get("fonte"))
    print("sector empresas:", len(sector.get("empresas") or []))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
