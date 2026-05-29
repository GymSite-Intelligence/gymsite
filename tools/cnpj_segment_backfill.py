#!/usr/bin/env python3
"""
Preenche segmento_operacao em registros já carregados no Supabase.

Uso:
  python tools/cnpj_segment_backfill.py --cidade Fortaleza --uf CE
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT / "frontend" / ".env", override=False)

from tools.cnpj_fitness_tools import _supabase_client
from tools.cnpj_segment_classifier import classificar_segmento_cnpj

PAGE = 500


def backfill_segmentos(*, cidade: str, uf: str = "") -> int:
    sb = _supabase_client()
    if sb is None:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY não configurados")

    offset = 0
    updated = 0
    while True:
        q = (
            sb.table("cnpj_fitness_estabelecimentos")
            .select(
                "id, cnpj, nome_fantasia, cnae_fiscal_principal, "
                "cnaes_secundarios, segmento_operacao"
            )
            .range(offset, offset + PAGE - 1)
        )
        if cidade:
            q = q.eq("cidade", cidade)
        if uf:
            q = q.eq("uf", uf[:2].upper())
        res = q.execute()
        rows = res.data or []
        if not rows:
            break

        for row in rows:
            if not isinstance(row, dict):
                continue
            seg = classificar_segmento_cnpj(
                row.get("nome_fantasia"),
                row.get("cnae_fiscal_principal"),
                row.get("cnaes_secundarios"),
            )
            if row.get("segmento_operacao") == seg:
                continue
            sb.table("cnpj_fitness_estabelecimentos").update(
                {"segmento_operacao": seg}
            ).eq("id", row["id"]).execute()
            updated += 1

        offset += PAGE
        print(f"processados {offset}… atualizados {updated}")

    return updated


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Backfill segmento_operacao (CNPJ)")
    ap.add_argument("--cidade", required=True)
    ap.add_argument("--uf", default="")
    args = ap.parse_args(argv)
    n = backfill_segmentos(cidade=args.cidade, uf=args.uf)
    print(f"[ok] {n} registros atualizados")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
