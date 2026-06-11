"""
Backfill de reviews com DOR para competidores de relatórios prontos.

Uso: python scripts/backfill_reviews_dores.py <relatorio_id> [...]

Problema que resolve (11/06/2026): Places Details devolve só 5 reviews
"mais relevantes" — enviesadas pro elogio (Smart Fit com 1.329 avaliações
e nenhuma ≤3★ no relatório). Aqui buscamos as 10 de MENOR NOTA via
SearchAPI (engine google_maps_reviews, sort_by=lowest_rating, pt-BR),
classificamos na taxonomia de dores com o Gemini batch já existente e
mesclamos ao array `reviews` do competidor (novas primeiro, cap 15).
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv(override=True)

import requests
from supabase import create_client

from tools.competitor_tools import (
    aplicar_classificacao_dores,
    classificar_dores_reviews_batch_gemini,
)

MAX_REVIEWS_TOTAL = 15


def buscar_reviews_baixa_nota(place_id: str) -> list[dict]:
    r = requests.get(
        "https://www.searchapi.io/api/v1/search",
        params={
            "engine": "google_maps_reviews",
            "place_id": place_id,
            "sort_by": "lowest_rating",
            "hl": "pt-br",
            "gl": "br",
            "api_key": os.environ["SEARCHAPI_KEY"],
        },
        timeout=60,
    )
    r.raise_for_status()
    out = []
    for rev in (r.json().get("reviews") or [])[:10]:
        texto = (rev.get("text") or rev.get("snippet") or "").strip()
        if not texto:
            continue
        try:
            rating = int(float(rev.get("rating") or 3))
        except (TypeError, ValueError):
            rating = 3
        out.append({
            "autor": (rev.get("user") or {}).get("name") or "anônimo",
            "rating": rating,
            "quote_curta": texto[:280],
            "data_relativa": rev.get("date") or "",
        })
    return out


def backfill(relatorio_id: str) -> None:
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    rows = (
        sb.table("competidores")
        .select("id, nome, place_id, reviews")
        .eq("relatorio_id", relatorio_id)
        .execute()
    ).data or []
    print(f"[{relatorio_id[:8]}] {len(rows)} competidores")

    pendentes = []
    for c in rows:
        pid = (c.get("place_id") or "").strip()
        if not pid:
            print(f"  - {c['nome']}: sem place_id")
            continue
        try:
            novas = buscar_reviews_baixa_nota(pid)
        except Exception as e:
            print(f"  - {c['nome']}: SearchAPI falhou ({type(e).__name__})")
            continue
        if not novas:
            print(f"  - {c['nome']}: nenhuma review de baixa nota")
            continue
        pendentes.append({"row": c, "nome": c["nome"], "reviews": novas})
        print(f"  · {c['nome']}: {len(novas)} reviews baixa nota coletadas")

    if not pendentes:
        print("  nada a classificar")
        return

    classificacoes = classificar_dores_reviews_batch_gemini(
        [{"nome": p["nome"], "reviews": p["reviews"]} for p in pendentes]
    )
    aplicar_classificacao_dores(
        [{"nome": p["nome"], "reviews": p["reviews"]} for p in pendentes],
        classificacoes,
    )

    for p in pendentes:
        antigas = p["row"].get("reviews") or []
        ids_novos = {(r["autor"], r["quote_curta"][:60]) for r in p["reviews"]}
        mantidas = [
            a for a in antigas
            if ((a.get("autor"), (a.get("quote_curta") or "")[:60]) not in ids_novos)
        ]
        merged = (p["reviews"] + mantidas)[:MAX_REVIEWS_TOTAL]
        sb.table("competidores").update({"reviews": merged}).eq("id", p["row"]["id"]).execute()
        dores = [r.get("categoria_dor") for r in p["reviews"] if r.get("categoria_dor") not in (None, "outra")]
        print(f"  + {p['nome']}: {len(merged)} reviews gravadas · dores: {sorted(set(dores)) or 'nenhuma'}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for rid in sys.argv[1:]:
        backfill(rid)
