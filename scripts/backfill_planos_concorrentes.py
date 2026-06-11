"""
Backfill de planos × preços × oferta dos concorrentes (dado na veia).

Uso: python scripts/backfill_planos_concorrentes.py <relatorio_id> [...]

Metodologia do doc docs/metodologia/analise_mercado_fitness_fortaleza.md:
academias trabalham com ~3 planos (entrada/intermediário/premium) e o
comparativo plano × preço × o-que-inclui é decisão de posicionamento na
veia. Busca via Gemini Search Grounding (cache 7d) por academia e grava
em competidores.planos_precos:
    [{"plano": "Black", "preco_mensal": "R$ 79,90",
      "inclui": ["musculação", "aulas", "app"], "fidelidade": "12 meses"}]
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv(override=True)

from supabase import create_client

from tools.gemini_search_grounding import pesquisar_no_google_grounding


def _extrair_json(texto: str) -> list | None:
    m = re.search(r"\[.*\]", texto, re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        return data if isinstance(data, list) else None
    except json.JSONDecodeError:
        return None


async def planos_de(nome: str, bairro: str, cidade: str) -> list | None:
    query = (
        f"Quais são os planos e preços de mensalidade da academia '{nome}' "
        f"({bairro or cidade}, {cidade})? Pesquise o site oficial e fontes recentes. "
        "Responda APENAS um JSON array (sem markdown), até 4 planos, no formato: "
        '[{"plano": "nome do plano", "preco_mensal": "R$ 99,90", '
        '"inclui": ["item1", "item2"], "fidelidade": "12 meses ou sem fidelidade"}]. '
        "Se não encontrar preços confiáveis, responda []."
    )
    cache_key = f"planos:{cidade.lower()}:{nome.lower()[:40]}"
    texto = await pesquisar_no_google_grounding(query, cache_key=cache_key)
    if not texto:
        return None
    return _extrair_json(texto)


async def backfill(relatorio_id: str) -> None:
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    inputs = (
        sb.table("relatorio_inputs")
        .select("cidade")
        .eq("relatorio_id", relatorio_id)
        .maybe_single()
        .execute()
    )
    cidade = (inputs.data or {}).get("cidade") or ""
    rows = (
        sb.table("competidores")
        .select("id, nome, bairro_concorrente, planos_precos")
        .eq("relatorio_id", relatorio_id)
        .execute()
    ).data or []
    print(f"[{relatorio_id[:8]}] {len(rows)} competidores ({cidade})")

    for c in rows:
        if c.get("planos_precos"):
            print(f"  - {c['nome']}: já tem planos")
            continue
        try:
            planos = await planos_de(c["nome"], c.get("bairro_concorrente") or "", cidade)
        except Exception as e:
            print(f"  - {c['nome']}: ERRO {type(e).__name__}: {e}")
            continue
        if not planos:
            print(f"  - {c['nome']}: sem preços confiáveis")
            continue
        planos = planos[:4]
        sb.table("competidores").update({"planos_precos": planos}).eq("id", c["id"]).execute()
        resumo = " | ".join(f"{p.get('plano')}: {p.get('preco_mensal')}" for p in planos if isinstance(p, dict))
        print(f"  + {c['nome']}: {resumo}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for rid in sys.argv[1:]:
        asyncio.run(backfill(rid))
