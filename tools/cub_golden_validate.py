"""Gate CUB estadual golden — 27 UFs, cub_m2 > 0, idade periodo_ref, ratio vs SINAPI opcional.

Uso:
  python -m tools.cub_golden_validate
  python -m tools.cub_golden_validate --max-idade-meses 4
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CUB_GOLDEN = ROOT / "data" / "cub_pilot" / "cub_estadual_golden.json"
SINAPI_GOLDEN = ROOT / "tools" / "fixtures" / "cub_sinapi" / "sinapi_snapshot_golden.json"

UFS_BR = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
    "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
    "RO", "RR", "RS", "SC", "SE", "SP", "TO",
]

_MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
}

RATIO_UF_MIN = 1.04
RATIO_UF_MAX = 1.10
RATIO_MEAN_MIN = 1.05
RATIO_MEAN_MAX = 1.09


def parse_periodo_ref(periodo: str | None) -> date | None:
    if not periodo or not isinstance(periodo, str):
        return None
    s = periodo.strip().lower()
    m = re.search(r"([a-zçã]+)\s+(\d{4})", s)
    if not m:
        return None
    mes_nome, ano_s = m.group(1), m.group(2)
    mes = _MESES.get(mes_nome)
    if not mes:
        return None
    try:
        return date(int(ano_s), mes, 1)
    except ValueError:
        return None


def _months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month)


def _is_proxy_fonte(fonte_uf: str | None) -> bool:
    return "proxy" in (fonte_uf or "").lower()


def validate_cub_snapshot(
    cub: dict[str, Any],
    *,
    sinapi: dict[str, Any] | None = None,
    hoje: date | None = None,
    max_idade_meses: int = 3,
) -> list[str]:
    """Return list of error messages; empty = ok."""
    hoje = hoje or date.today()
    errs: list[str] = []
    por = cub.get("por_uf") if isinstance(cub.get("por_uf"), dict) else {}
    have = {str(k).upper() for k in por}
    missing = [u for u in UFS_BR if u not in have]
    extra = sorted(have - set(UFS_BR))
    if missing:
        errs.append(f"faltando {len(missing)} UF(s) de 27: {', '.join(missing)}")
    if extra:
        errs.append(f"UF inesperada(s): {', '.join(extra)}")

    for uf in UFS_BR:
        block = por.get(uf) or por.get(uf.lower())
        if not isinstance(block, dict):
            continue
        raw = block.get("cub_m2")
        try:
            cub_m2 = float(raw) if raw is not None else None
        except (TypeError, ValueError):
            cub_m2 = None
        if cub_m2 is None or cub_m2 <= 0:
            errs.append(f"{uf}: cub_m2 inválido ({raw!r})")
            continue

        periodo = block.get("periodo_ref")
        fonte = block.get("fonte_uf")
        ref = parse_periodo_ref(str(periodo) if periodo else None)
        if ref is None:
            errs.append(f"{uf}: periodo_ref não parseável ({periodo!r})")
            continue
        idade = _months_between(ref, hoje)
        if idade > max_idade_meses and not _is_proxy_fonte(str(fonte) if fonte else None):
            errs.append(
                f"{uf}: periodo_ref atrasado ({periodo}, {idade} meses > {max_idade_meses})"
                f" — atualizar CUB ou marcar fonte_uf com 'proxy'"
            )

    if sinapi and isinstance(sinapi.get("por_uf"), dict):
        ratios: list[float] = []
        sin_por = sinapi["por_uf"]
        for uf in UFS_BR:
            cblock = por.get(uf) or {}
            sblock = sin_por.get(uf) or {}
            try:
                c = float(cblock.get("cub_m2"))
                s = float(sblock.get("sinapi_custo_m2"))
            except (TypeError, ValueError):
                continue
            if s <= 0:
                continue
            ratio = c / s
            ratios.append(ratio)
            if ratio < RATIO_UF_MIN or ratio > RATIO_UF_MAX:
                errs.append(
                    f"{uf}: ratio CUB/SINAPI {ratio:.4f} fora [{RATIO_UF_MIN}, {RATIO_UF_MAX}]"
                )
        if len(ratios) >= 20:
            mean = statistics.mean(ratios)
            if mean < RATIO_MEAN_MIN or mean > RATIO_MEAN_MAX:
                errs.append(
                    f"ratio médio CUB/SINAPI {mean:.4f} fora [{RATIO_MEAN_MIN}, {RATIO_MEAN_MAX}]"
                )

    return errs


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Valida CUB golden estadual")
    p.add_argument("--cub", type=Path, default=CUB_GOLDEN)
    p.add_argument("--sinapi", type=Path, default=None, help="Opcional; default fixture se existir")
    p.add_argument("--max-idade-meses", type=int, default=3)
    p.add_argument("--skip-ratio", action="store_true")
    args = p.parse_args(argv)

    cub = json.loads(args.cub.read_text(encoding="utf-8"))
    sinapi = None
    if not args.skip_ratio:
        sin_path = args.sinapi or SINAPI_GOLDEN
        if sin_path.is_file():
            sinapi = json.loads(sin_path.read_text(encoding="utf-8"))

    errs = validate_cub_snapshot(
        cub,
        sinapi=sinapi,
        hoje=date.today(),
        max_idade_meses=args.max_idade_meses,
    )
    if not errs:
        print("OK: CUB golden passou no gate")
        return 0
    print("FAIL: CUB golden")
    for e in errs:
        print(f"  - {e}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
