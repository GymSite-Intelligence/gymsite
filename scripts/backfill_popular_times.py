"""
Backfill de horários de pico em competidores de relatórios já gerados.

Uso: python scripts/backfill_popular_times.py <relatorio_id> [<relatorio_id> ...]

Para cada competidor com place_id e sem horarios_pico, consulta
pesquisar_horarios_pico (Tier 0 SearchAPI com cache 7d) e grava
horarios_pico + pico_semanal — mesmo shape do pipeline (competitor_tools).
Criado 11/06/2026: relatórios Bessa/Cocó rodaram com a quota SearchAPI
esgotada e ficaram com Pico vazio.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv(override=True)

from supabase import create_client

from tools.popular_times_tool import pesquisar_horarios_pico


async def backfill(relatorio_id: str) -> None:
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    rows = (
        sb.table("competidores")
        .select("id, nome, place_id, lat, lng, horarios_pico")
        .eq("relatorio_id", relatorio_id)
        .execute()
    ).data or []
    print(f"[{relatorio_id[:8]}] {len(rows)} competidores")

    atualizados = 0
    for c in rows:
        pid = (c.get("place_id") or "").strip()
        if not pid:
            print(f"  - {c['nome']}: sem place_id, pulando")
            continue
        if c.get("horarios_pico"):
            print(f"  - {c['nome']}: já tem pico, pulando")
            continue
        try:
            maps_url = f"https://www.google.com/maps/place/?q=place_id:{pid}"
            r = await pesquisar_horarios_pico(
                maps_url,
                pid,
                nome=c["nome"],
                lat=c.get("lat"),
                lng=c.get("lng"),
                force_refresh=True,
            )
        except Exception as e:
            print(f"  - {c['nome']}: ERRO {type(e).__name__}: {e}")
            continue

        if r.get("status") != "ok" or not r.get("dados_por_dia"):
            print(f"  - {c['nome']}: {r.get('status')} (sem dados)")
            continue

        dia_top = r.get("dia_mais_movimentado") or {}
        pico_semanal = None
        if dia_top.get("dia") and dia_top.get("hora"):
            pico_semanal = (
                f"{dia_top['dia'].capitalize()} {dia_top['hora']}h "
                f"({dia_top.get('percentual', 0)}%)"
            )
        sb.table("competidores").update({
            "horarios_pico": r["dados_por_dia"],
            "pico_semanal": pico_semanal,
        }).eq("id", c["id"]).execute()
        atualizados += 1
        print(f"  + {c['nome']}: {pico_semanal or 'curva gravada'}")

    print(f"[{relatorio_id[:8]}] {atualizados} atualizados")


async def main() -> None:
    for rid in sys.argv[1:]:
        await backfill(rid)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    asyncio.run(main())
