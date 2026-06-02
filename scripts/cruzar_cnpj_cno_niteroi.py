#!/usr/bin/env python3
"""Compat: use scripts/query_cnpj_cno.py --cidade Niterói --uf RJ"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "query_cnpj_cno.py"

if __name__ == "__main__":
    cmd = [sys.executable, str(SCRIPT), "--cidade", "Niterói", "--uf", "RJ", *sys.argv[1:]]
    raise SystemExit(subprocess.call(cmd))
