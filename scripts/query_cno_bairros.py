#!/usr/bin/env python3
"""Compat: delega para query_cnpj_cno.py (fluxo CNPJ → CNO, município + bairros)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "query_cnpj_cno.py"


def main() -> None:
    # Defaults vazios — passe --cidade/--uf/--bairros na CLI
    cmd = [sys.executable, str(SCRIPT), *sys.argv[1:]]
    if len(sys.argv) == 1:
        cmd.extend(
            [
                "--cidade",
                "Niterói",
                "--uf",
                "RJ",
                "--bairros",
                "Itaipu,Piratininga,Camboinhas",
                "--json-out",
                str(
                    ROOT
                    / "eval"
                    / "golden_dataset"
                    / "niteroi_camboinhas_20260513"
                    / "cno_cruzamento_cnpj.json"
                ),
            ]
        )
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
