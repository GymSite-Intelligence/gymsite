#!/usr/bin/env python3
"""Gera PDF de exemplo a partir de mock JSON ou relatório real via API."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pdf import LayoutId, generate_relatorio_pdf
from pdf.adapters import relatorio_from_api_payload, relatorio_from_nested_json


def main() -> None:
    p = argparse.ArgumentParser(description="Gera PDF GymSite de amostra")
    p.add_argument("--mock", type=Path, help="JSON canônico (ex: mocks/rpt_*.json)")
    p.add_argument("--relatorio-id", help="UUID — busca via Supabase/API se .env ok")
    p.add_argument(
        "--layout",
        choices=[x.value for x in LayoutId],
        default=LayoutId.CLASSIC.value,
    )
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=_ROOT / "artifacts" / "gymsite-relatorio-sample.pdf",
    )
    args = p.parse_args()

    if args.mock:
        data = json.loads(args.mock.read_text(encoding="utf-8"))
        model = relatorio_from_nested_json(data)
    elif args.relatorio_id:
        from dotenv import load_dotenv

        load_dotenv(_ROOT / ".env")
        from api import get_relatorio  # noqa: WPS433 — script de dev

        payload = get_relatorio(args.relatorio_id)
        model = relatorio_from_api_payload(payload)
    else:
        default_mock = _ROOT / "frontend" / "src" / "mocks" / "relatorios" / "rpt_1778468764.json"
        if not default_mock.exists():
            p.error("Informe --mock ou --relatorio-id")
        data = json.loads(default_mock.read_text(encoding="utf-8"))
        model = relatorio_from_nested_json(data)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    pdf = generate_relatorio_pdf(model, layout=args.layout)
    args.output.write_bytes(pdf)
    print(f"OK: {args.output} ({len(pdf):,} bytes) layout={args.layout}")


if __name__ == "__main__":
    main()
