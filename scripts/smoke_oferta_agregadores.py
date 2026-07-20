#!/usr/bin/env python3
"""Smoke SPEC_OFERTA_AGREGADORES — Wellhub HTML ao vivo (caso Cocó).

Uso:
  .venv/Scripts/python.exe scripts/smoke_oferta_agregadores.py

Valida: URL parceiro → httpx → tier_agregador.plano + preco_mensal_brl.
Tier ≠ mensalidade de balcão (rótulo obrigatório).
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

import httpx

from tools.agregadores_fetcher import coletar_agregadores

# Aceitação SPEC §5 — Cocó
_CASOS = [
    {"nome": "CT Greenlife", "cidade": "Fortaleza", "espera_tier": True},
    {"nome": "Parque Esportes", "cidade": "Fortaleza", "espera_tier": True},
    {"nome": "VS Club", "cidade": "Fortaleza", "espera_tier": False},  # Gurupass off
    {"nome": "Smart Fit", "cidade": "Fortaleza", "espera_tier": True},
]


async def _um(client: httpx.AsyncClient, caso: dict) -> dict:
    t0 = time.perf_counter()
    out = await coletar_agregadores(client, caso["nome"], caso["cidade"])
    ms = round((time.perf_counter() - t0) * 1000)
    extras = out.get("extras") or {}
    tier = extras.get("tier_agregador") if isinstance(extras.get("tier_agregador"), dict) else None
    rating = extras.get("rating_agregador") if isinstance(extras.get("rating_agregador"), dict) else None
    return {
        "nome": caso["nome"],
        "ms": ms,
        "fontes_ok": out.get("fontes_ok") or [],
        "tem_texto": bool(out.get("textos")),
        "tier_plano": (tier or {}).get("plano"),
        "tier_preco_brl": (tier or {}).get("preco_mensal_brl"),
        "tier_obs": (tier or {}).get("observacao"),
        "rating": (rating or {}).get("nota"),
        "avaliacoes": (rating or {}).get("avaliacoes"),
        "instagram": extras.get("instagram_handle"),
        "comodidades_n": len(extras.get("comodidades") or []),
        "tem_preco_plano": bool((tier or {}).get("preco_mensal_brl")),
        "espera_tier": caso.get("espera_tier"),
    }


async def main() -> int:
    print("=== SMOKE SPEC_OFERTA_AGREGADORES (Wellhub) ===\n")
    rows: list[dict] = []
    async with httpx.AsyncClient(
        headers={"User-Agent": "GymSiteIntelligence/smoke-agregadores"},
        follow_redirects=True,
        timeout=20.0,
    ) as client:
        for caso in _CASOS:
            row = await _um(client, caso)
            rows.append(row)
            preco = row["tier_preco_brl"]
            flag = "OK" if row["tem_preco_plano"] else ("MISS" if row["espera_tier"] else "N/A")
            print(
                f"[{flag}] {row['nome']}: fontes={row['fontes_ok']} "
                f"plano={row['tier_plano']} preco={preco} "
                f"rating={row['rating']} ig={row['instagram']} "
                f"comod={row['comodidades_n']} ({row['ms']}ms)"
            )

    com_preco = [r for r in rows if r["tem_preco_plano"]]
    esperados = [r for r in rows if r["espera_tier"]]
    miss = [r for r in esperados if not r["tem_preco_plano"]]

    print("\n==== RESUMO ====")
    print(f"casos={len(rows)} com_tier_preco={len(com_preco)} miss_esperados={len(miss)}")
    if miss:
        print("SEM PRECO (esperavam Wellhub):", ", ".join(r["nome"] for r in miss))
    else:
        print("todos casos com espera_tier trouxeram preco_mensal_brl")

    # balcão check: nenhum resultado deve fingir balcão
    for r in com_preco:
        obs = r.get("tier_obs") or ""
        if "não é mensalidade de balcão" not in obs:
            print(f"FAIL rotulo balcão: {r['nome']}")
            return 2

    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 1 if miss else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
