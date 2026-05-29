#!/usr/bin/env python3
"""CLI: python tools/maps_health_check.py"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT / "frontend" / ".env", override=False)

from tools.maps_health import check_google_maps


def main() -> int:
    r = check_google_maps()
    print(json.dumps(r, indent=2, ensure_ascii=False))
    if r.get("ok"):
        print("\nOK — Google Maps operacional.")
        return 0
    print("\nFALHA — siga remediation acima ou use fallback OSM (MAPS_FALLBACK_ENABLED=1).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
