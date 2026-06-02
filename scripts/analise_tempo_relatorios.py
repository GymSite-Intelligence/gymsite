#!/usr/bin/env python3
"""Estatísticas de tempo_execucao_segundos (relatórios concluídos)."""
from __future__ import annotations

import os
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def main() -> int:
    from supabase import create_client  # type: ignore[reportAttributeAccessIssue]

    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        print("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY ausentes", file=sys.stderr)
        return 1

    sb = create_client(url, key)
    rows = (
        sb.table("relatorios")
        .select(
            "id,status,tempo_execucao_segundos,created_at,tokens_total,custo_brl,erro_mensagem"
        )
        .order("created_at", desc=True)
        .execute()
        .data
        or []
    )

    done = [r for r in rows if r.get("status") == "done" and r.get("tempo_execucao_segundos")]
    tempos = [int(r["tempo_execucao_segundos"]) for r in done]

    def fmt_min(s: float) -> str:
        return f"{s / 60:.1f} min ({s:.0f}s)"

    def pct(vals: list[int], p: float) -> float:
        s = sorted(vals)
        k = (len(s) - 1) * p
        f = int(k)
        c = min(f + 1, len(s) - 1)
        return s[f] + (s[c] - s[f]) * (k - f)

    print("=== Tempo de conclusão — relatórios (Supabase) ===\n")
    print(f"Total na base: {len(rows)}")
    print(f"Concluídos (done) com tempo: {len(tempos)}\n")

    if not tempos:
        print("Sem dados de tempo_execucao_segundos.")
        return 0

    under5 = sum(1 for t in tempos if t <= 300)
    under10 = sum(1 for t in tempos if t <= 600)
    p75 = pct(tempos, 0.75)

    print("--- Distribuição ---")
    print(f"Média:    {fmt_min(statistics.mean(tempos))}")
    print(f"Mediana:  {fmt_min(statistics.median(tempos))}")
    print(f"P25:      {fmt_min(pct(tempos, 0.25))}")
    print(f"P75:      {fmt_min(p75)}")
    print(f"Min/Max:  {fmt_min(min(tempos))} / {fmt_min(max(tempos))}")
    print()
    print(f"<= 5 min (300s):  {under5}/{len(tempos)} ({100 * under5 / len(tempos):.0f}%)")
    print(f"<= 10 min (600s): {under10}/{len(tempos)} ({100 * under10 / len(tempos):.0f}%)")
    print()
    print("--- ETA sugerido na UI ---")
    print(f"Típico (mediana):     ~{round(statistics.median(tempos) / 60)} min")
    print(f"Conservador (P75):    ~{round(p75 / 60)} min")
    print(f"Marketing atual (~5 min): cobre {100 * under5 / len(tempos):.0f}% dos casos")
    print()

    outliers = [r for r in done if r["tempo_execucao_segundos"] > 1200]
    if outliers:
        print(f"--- Outliers > 20 min ({len(outliers)}) ---")
        for r in outliers[:10]:
            t = r["tempo_execucao_segundos"]
            print(
                f"  {t}s ({t/60:.1f}min) | tokens={r.get('tokens_total')} | "
                f"created={str(r.get('created_at', ''))[:10]}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
