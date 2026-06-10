#!/usr/bin/env python3
"""Descobre datasets CKAN relevantes para cidade/UF (demografia)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "data" / "ckan_catalog"


def main() -> int:
    p = argparse.ArgumentParser(description="CKAN package_search por cidade")
    p.add_argument("--cidade", required=True)
    p.add_argument("--uf", default="CE")
    p.add_argument("--portal", default="https://dados.gov.br")
    args = p.parse_args()

    from tools.ckan_client import search_datasets_for_city

    datasets = search_datasets_for_city(args.cidade, args.uf, portal_base=args.portal)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = f"{args.cidade}_{args.uf}".lower().replace(" ", "_")
    out = OUT_DIR / f"{slug}.json"
    payload = {
        "cidade": args.cidade,
        "uf": args.uf,
        "portal": args.portal,
        "datasets_matched": datasets,
        "count": len(datasets),
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"found={len(datasets)} written={out}")
    for d in datasets[:5]:
        print(f"  - {d.get('title')} ({d.get('id')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
