#!/usr/bin/env python3
"""Backfill async de razao_social em cnpj_fitness_estabelecimentos.

Não bloqueia o load JSON/ZIP. Reusa tools.cnpj_enrichment / cache ReceitaWS.

Uso:
  python scripts/backfill_cnpj_razao_social.py --limit 20 --dry-run
  python scripts/backfill_cnpj_razao_social.py --ref 2026-05 --limit 100
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Backfill razao_social CNPJ fitness")
    ap.add_argument("--ref", default="", help="YYYY-MM (filtra ref_month); vazio = qualquer")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.4, help="Pausa entre enrich (s)")
    args = ap.parse_args(argv)

    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        print("SUPABASE_URL / SERVICE_ROLE_KEY missing", file=sys.stderr)
        return 1

    from supabase import create_client

    from tools.cnpj_enrichment import enriquecer_entrante_unico
    from tools.db_schema import tbl

    sb = create_client(url, key)
    q = (
        tbl(sb, "cnpj_fitness_estabelecimentos")
        .select("cnpj, nome_fantasia, razao_social, ref_month")
        .is_("razao_social", "null")
        .limit(max(1, min(args.limit, 500)))
    )
    if args.ref:
        ref = args.ref.strip()
        if len(ref) == 7:
            ref = f"{ref}-01"
        q = q.eq("ref_month", ref)
    res = q.execute()
    rows = [r for r in (res.data or []) if isinstance(r, dict)]
    print(f"candidatos sem razao_social: {len(rows)}")
    updated = 0
    for r in rows:
        cnpj = str(r.get("cnpj") or "").strip()
        if not cnpj:
            continue
        if args.dry_run:
            print(f"[dry-run] would enrich {cnpj}")
            continue
        try:
            out, _meta = enriquecer_entrante_unico(
                {
                    "cnpj": cnpj,
                    "nome_fantasia": r.get("nome_fantasia"),
                    "razao_social": None,
                },
                usar_apollo=False,
                forcar_receita=True,
            )
        except Exception as exc:
            print(f"skip {cnpj}: {exc}")
            time.sleep(args.sleep)
            continue
        razao = (out.get("razao_social") or "").strip() if isinstance(out, dict) else ""
        if not razao:
            time.sleep(args.sleep)
            continue
        tbl(sb, "cnpj_fitness_estabelecimentos").update(
            {"razao_social": razao}
        ).eq("cnpj", cnpj).execute()
        updated += 1
        print(f"ok {cnpj}: {razao[:60]}")
        time.sleep(args.sleep)
    print(f"updated={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
