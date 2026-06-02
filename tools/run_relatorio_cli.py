#!/usr/bin/env python3
"""
Dispara um relatório pelo pipeline ADK (CLI).

Cria stub em relatorios + relatorio_inputs (igual POST /api/relatorios) antes
de rodar o pipeline — evita falha de FK na persistência do A6.

Uso:
  python tools/run_relatorio_cli.py --cidade Fortaleza --bairro Meireles --uf CE \\
    --area-min 800 --area-max 1500 --preset m
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT / "frontend" / ".env", override=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cidade", default="Fortaleza")
    ap.add_argument("--bairro", default="Meireles")
    ap.add_argument("--uf", default="CE")
    ap.add_argument("--area-min", type=int, default=800)
    ap.add_argument("--area-max", type=int, default=1500)
    ap.add_argument("--preset", default="m")
    ap.add_argument(
        "--research",
        choices=("auto", "gemini", "kimi"),
        default="auto",
        help="Provedor A0: gemini | kimi | auto",
    )
    args = ap.parse_args()

    from api import NovoRelatorioInput, _run_pipeline_async
    from tools.postgrest_sb import create_relatorio_stub_postgrest

    payload = NovoRelatorioInput(
        cidade=args.cidade,
        bairro=args.bairro,
        uf=args.uf,
        area_m2_min=args.area_min,
        area_m2_max=args.area_max,
        tamanho_preset=args.preset,
        a0_research_provider=args.research,
    )

    try:
        relatorio_id, _created_at = create_relatorio_stub_postgrest(payload)
    except RuntimeError as e:
        print(f"Erro ao criar stub: {e}", file=sys.stderr)
        return 1

    print(f"Iniciando pipeline relatorio_id={relatorio_id}")
    print(f"  {args.bairro} / {args.cidade}-{args.uf}  {args.area_min}-{args.area_max}m²")
    t0 = time.time()
    asyncio.run(_run_pipeline_async(relatorio_id, payload))
    print(f"Concluído em {time.time() - t0:.0f}s — id={relatorio_id}")
    print(f"Viewer: /relatorios/{relatorio_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
