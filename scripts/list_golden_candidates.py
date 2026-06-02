#!/usr/bin/env python3
"""Lista candidatos a golden cases no Supabase (exclui já aprovados)."""
from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

APPROVED = {
    "8845b104-4536-444e-98d6-03b7319cbf08",
    "291f1a1f-1303-4da4-b487-bafaa3cc020e",
}


def main() -> None:
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise SystemExit("SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY ausentes no .env")

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }
    path = (
        "v_relatorios_resumo?select=id,created_at,cidade,bairro,uf,veredito,"
        "score_top1_candidato,score_bairro,modelo_recomendado,nivel_saturacao,status"
        "&status=eq.done&order=created_at.desc&limit=150"
    )
    r = httpx.get(f"{url}/rest/v1/{path}", headers=headers, timeout=60)
    r.raise_for_status()
    rows = [
        row
        for row in (r.json() or [])
        if row.get("id") not in APPROVED and row.get("veredito")
    ]

    print(f"Total candidatos (done, com veredito): {len(rows)}\n")
    print("Vereditos:", dict(Counter(row["veredito"] for row in rows)))
    print()

    def score(row: dict) -> float:
        return float(row.get("score_top1_candidato") or row.get("score_bairro") or 0)

    def show(title: str, filt, limit: int = 8) -> None:
        picked = [row for row in rows if filt(row)][:limit]
        print(f"=== {title} ({len(picked)} shown) ===")
        for row in picked:
            s = row.get("score_top1_candidato") or row.get("score_bairro")
            print(
                f"{row['id']} | {row['created_at'][:10]} | "
                f"{row.get('cidade', '?'):15} | {row.get('bairro', '?'):20} | "
                f"{row.get('veredito', '?'):25} | score={s} | "
                f"{row.get('modelo_recomendado', '')}"
            )
        print()

    show(
        "CASO 3 — APROVADO puro (score_top1 >= 8)",
        lambda row: row["veredito"] == "APROVADO"
        and (row.get("score_top1_candidato") or 0) >= 8,
    )
    show(
        "CASO 3 alt — APROVADO puro (max score >= 8)",
        lambda row: row["veredito"] == "APROVADO" and score(row) >= 8,
    )
    show(
        "CASO 4 — INVESTIGAR/REPROVADO (score < 6)",
        lambda row: row["veredito"]
        in ("INVESTIGAR MAIS", "REPROVADO", "INVESTIGAR")
        and score(row) < 6,
    )
    show(
        "CASO 4 alt — veredito negativo (qualquer score)",
        lambda row: "REPROV" in (row.get("veredito") or "")
        or "INVESTIG" in (row.get("veredito") or ""),
    )
    show(
        "CASO 5 — Borda score ~6.0",
        lambda row: abs(score(row) - 6.0) <= 0.15,
    )
    show(
        "CASO 5 — Borda score ~8.0",
        lambda row: abs(score(row) - 8.0) <= 0.15,
    )
    show(
        "APROVADO COM RESSALVAS (extra)",
        lambda row: row["veredito"] == "APROVADO COM RESSALVAS",
        limit=5,
    )


if __name__ == "__main__":
    main()
