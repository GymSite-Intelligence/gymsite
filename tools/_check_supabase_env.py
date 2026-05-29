"""Diagnóstico rápido: o loader enxerga SUPABASE_* no .env?"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
paths = [
    _ROOT / ".env",
    _ROOT / "frontend" / ".env",
    _ROOT / "db" / ".env",
    _ROOT / "gymsite_intelligence" / ".env",
]
for p in paths:
    loaded = load_dotenv(p, override=False)
    print(f"{'ok' if loaded else '--':8} {p}")

url = os.getenv("SUPABASE_URL", "")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
print("SUPABASE_URL:", "set" if url else "MISSING")
print("SUPABASE_SERVICE_ROLE_KEY:", "set" if key else "MISSING")
sys.exit(0 if url and key else 1)
