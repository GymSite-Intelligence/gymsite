#!/usr/bin/env python3
"""Valida ROI: execucao nova vs baseline (logs_antigos.json)."""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

LOGS_DEFAULT = Path(__file__).resolve().parent / "logs_antigos.json"


def _delta_pct(baseline: float, novo: float) -> float:
    if baseline <= 0:
        return 0.0
    return (baseline - novo) / baseline * 100.0


def _median(vals: list[float]) -> float:
    return float(statistics.median(vals)) if vals else 0.0


GO_TEMPO_S = 150.0
GO_CUSTO_BRL = 1.30
GO_TOKENS = 150_000
MIN_REDUCAO_PCT = 70.0


def _verdict(
    novo_t: float,
    novo_c: float,
    novo_k: float,
    *,
    base_t: float = 766.0,
    base_c: float = 4.45,
) -> str:
    dt = _delta_pct(base_t, novo_t)
    dc = _delta_pct(base_c, novo_c)
    if dt < MIN_REDUCAO_PCT or dc < MIN_REDUCAO_PCT:
        return "NO-GO"
    hits = sum(
        [
            novo_t <= GO_TEMPO_S,
            novo_c <= GO_CUSTO_BRL,
            novo_k <= GO_TOKENS,
        ]
    )
    if hits == 3:
        return "GO"
    if hits >= 1:
        return "AJUSTAR"
    return "NO-GO"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--logs", default=str(LOGS_DEFAULT))
    p.add_argument("--tempo", type=float, default=90.0)
    p.add_argument("--custo", type=float, default=0.85)
    p.add_argument("--tokens", type=int, default=65000)
    p.add_argument("positional", nargs="*", help="(legado) tempo custo tokens")
    args = p.parse_args()

    if args.positional:
        if len(args.positional) >= 1:
            args.tempo = float(args.positional[0])
        if len(args.positional) >= 2:
            args.custo = float(args.positional[1])
        if len(args.positional) >= 3:
            args.tokens = int(float(args.positional[2]))

    path = Path(args.logs)
    if not path.exists():
        print("Arquivo baseline ausente: %s" % path, file=sys.stderr)
        return 1
    logs = json.loads(path.read_text(encoding="utf-8"))
    done = [x for x in logs if x.get("status") == "done"]
    tempos = [float(x["tempo_execucao_segundos"]) for x in done if x.get("tempo_execucao_segundos")]
    custos = [float(x["custo_total_brl"]) for x in done if x.get("custo_total_brl") is not None]
    tokens = [float(x["tokens_in_total"]) for x in done if x.get("tokens_in_total")]

    base_t = _median(tempos)
    base_c = _median(custos)
    base_k = _median(tokens)

    novo = {
        "tempo_execucao_segundos": args.tempo,
        "custo_total_brl": args.custo,
        "tokens_in_total": float(args.tokens),
        "status": "done",
    }

    print("=== ROI validator ===")
    print("Baseline runs: %d (fonte: %s)" % (len(done), path.name))
    print(
        "Mediana tempo (s): %.1f | custo (BRL): %.2f | tokens_in: %.0f"
        % (base_t, base_c, base_k)
    )
    print(
        "Novo run       : %.1fs | %.2f BRL | %.0f tokens"
        % (novo["tempo_execucao_segundos"], novo["custo_total_brl"], novo["tokens_in_total"])
    )
    print()
    dt = _delta_pct(base_t, novo["tempo_execucao_segundos"])
    dc = _delta_pct(base_c, novo["custo_total_brl"])
    dk = _delta_pct(base_k, novo["tokens_in_total"])
    print("Delta tempo:  %+.1f%% (positivo = mais rapido)" % dt)
    print("Delta custo:  %+.1f%% (positivo = mais barato)" % dc)
    print("Delta tokens: %+.1f%% (positivo = menos tokens)" % dk)
    print()
    verdict = _verdict(
        novo["tempo_execucao_segundos"],
        novo["custo_total_brl"],
        novo["tokens_in_total"],
        base_t=base_t,
        base_c=base_c,
    )
    print("=== Veredito (refs GO: <=%ds, <=R$%.2f, <=%dk tokens) ===" % (GO_TEMPO_S, GO_CUSTO_BRL, GO_TOKENS // 1000))
    print("Veredito:", verdict)
    go_hits = [
        novo["tempo_execucao_segundos"] <= GO_TEMPO_S,
        novo["custo_total_brl"] <= GO_CUSTO_BRL,
        novo["tokens_in_total"] <= GO_TOKENS,
    ]
    print(
        "Criterios GO: tempo=%s custo=%s tokens=%s"
        % tuple("OK" if x else "FORA" for x in go_hits)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
