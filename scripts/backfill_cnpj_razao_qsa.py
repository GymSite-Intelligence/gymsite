#!/usr/bin/env python3
"""
Backfill de razão social e QSA para CNPJs fitness já carregados no Supabase.

Uso:
  python scripts/backfill_cnpj_razao_qsa.py --cidade "Ribeirão Preto" --uf SP
  python scripts/backfill_cnpj_razao_qsa.py --cidade Fortaleza --uf CE --limit 100

Busca CNPJs sem razão social ou sem QSA e enriquece via ReceitaWS + Apollo
(opcional), atualizando a tabela cnpj_fitness_estabelecimentos e o cache.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT / "frontend" / ".env", override=False)

from tools.cnpj_fitness_tools import _supabase_client
from tools.cnpj_enrichment import enriquecer_entrantes

PAGE = 100


def backfill_razao_qsa(
    *, cidade: str, uf: str = "", limit: int | None = None, usar_apollo: bool = False
) -> dict[str, int]:
    sb = _supabase_client()
    if sb is None:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY não configurados")

    offset = 0
    total_atualizados = 0
    total_receita_calls = 0
    total_cache_hits = 0

    while True:
        q = (
            sb.table("cnpj_fitness_estabelecimentos")
            .select(
                "id, cnpj, nome_fantasia, razao_social, bairro, email, telefone"
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

        # Seleciona apenas CNPJs que precisam de enriquecimento
        precisam: list[dict] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            precisa = (
                not (row.get("razao_social") or "").strip()
                or not (row.get("bairro") or "").strip()
                or not (row.get("email") or "").strip()
                or not (row.get("telefone") or "").strip()
            )
            if precisa:
                precisam.append(row)

        if precisam:
            entrantes = [{"cnpj": r["cnpj"]} for r in precisam]
            enriched, meta = enriquecer_entrantes(
                entrantes, max_receita=50, usar_apollo=usar_apollo
            )
            total_receita_calls += int(meta.get("receita_chamadas") or 0)
            total_cache_hits += int(meta.get("cache_hits") or 0)

            for orig, ent in zip(precisam, enriched):
                updates: dict[str, str | None] = {}
                if ent.get("razao_social"):
                    updates["razao_social"] = ent["razao_social"]
                if ent.get("bairro"):
                    updates["bairro"] = ent["bairro"]
                if ent.get("email_empresa"):
                    updates["email"] = ent["email_empresa"]
                if ent.get("telefone_empresa"):
                    updates["telefone"] = ent["telefone_empresa"]
                if updates:
                    sb.table("cnpj_fitness_estabelecimentos").update(updates).eq(
                        "id", orig["id"]
                    ).execute()
                    total_atualizados += 1

        offset += PAGE
        print(f"processados {offset}… atualizados {total_atualizados}")

        if limit and total_atualizados >= limit:
            print(f"[info] limite de {limit} atualizações atingido")
            break

    return {
        "atualizados": total_atualizados,
        "receita_chamadas": total_receita_calls,
        "cache_hits": total_cache_hits,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Backfill razão social + QSA para CNPJs fitness existentes"
    )
    ap.add_argument("--cidade", required=True, help="Cidade alvo (ex: Ribeirão Preto)")
    ap.add_argument("--uf", default="", help="UF (ex: SP)")
    ap.add_argument("--limit", type=int, default=0, help="Máximo de registros a atualizar")
    ap.add_argument("--apollo", action="store_true", help="Também buscar contato via Apollo")
    args = ap.parse_args(argv)

    result = backfill_razao_qsa(
        cidade=args.cidade,
        uf=args.uf,
        limit=args.limit or None,
        usar_apollo=args.apollo,
    )
    print(
        f"[ok] {result['atualizados']} registros atualizados | "
        f"ReceitaWS: {result['receita_chamadas']} chamadas | "
        f"cache: {result['cache_hits']} hits"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
