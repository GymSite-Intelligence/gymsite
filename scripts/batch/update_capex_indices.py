#!/usr/bin/env python3
"""Atualiza metrics/cache/capex_indices.json via SINAPI/SIDRA (tabela 2296)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    from tools.sinapi_indices import atualizar_capex_indices

    snap = atualizar_capex_indices()
    ufs = snap.get("por_uf") or {}
    print("written: metrics/cache/capex_indices.json")
    print("periodo:", snap.get("periodo_ref"))
    print("ufs:", len(ufs))
    for uf in ("CE", "SP", "PR", "DF", "RJ"):
        b = ufs.get(uf)
        if b:
            print(f"  {uf} sinapi_m2={b.get('sinapi_custo_m2')} obra_mid={b.get('obra_adaptacao_por_m2', {}).get('mid')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
