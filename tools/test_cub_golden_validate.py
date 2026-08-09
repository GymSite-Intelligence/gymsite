"""TDD — gate CUB golden (27 UF, cub_m2, idade, ratio vs SINAPI)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from tools.cub_golden_validate import UFS_BR, validate_cub_snapshot

ROOT = Path(__file__).resolve().parents[1]


def _full_por_uf(cub_m2: float = 2000.0, periodo: str = "junho 2026", fonte: str = "SindusCon-XX"):
    return {
        uf: {"cub_m2": cub_m2, "periodo_ref": periodo, "fonte_uf": fonte.replace("XX", uf)}
        for uf in UFS_BR
    }


def test_missing_uf_errors():
    bad = {
        "por_uf": {"CE": {"cub_m2": 1000, "periodo_ref": "junho 2026", "fonte_uf": "SindusCon-CE"}},
        "data_coleta": "2026-07-13",
    }
    errs = validate_cub_snapshot(bad, sinapi=None, hoje=date(2026, 8, 6))
    assert any("27" in e or "UF" in e.upper() or "faltando" in e.lower() for e in errs)


def test_zero_cub_m2_errors():
    por = _full_por_uf()
    por["CE"]["cub_m2"] = 0
    errs = validate_cub_snapshot(
        {"por_uf": por, "data_coleta": "2026-07-13"},
        sinapi=None,
        hoje=date(2026, 8, 6),
    )
    assert any("CE" in e and ("cub_m2" in e.lower() or "0" in e) for e in errs)


def test_stale_periodo_fails_unless_proxy():
    por = _full_por_uf(periodo="junho 2026")
    por["MS"]["periodo_ref"] = "maio 2025"
    por["MS"]["fonte_uf"] = "SindusCon-MS"
    errs = validate_cub_snapshot(
        {"por_uf": por, "data_coleta": "2026-07-13"},
        sinapi=None,
        hoje=date(2026, 8, 6),
        max_idade_meses=3,
    )
    assert any("MS" in e and "atrasado" in e.lower() for e in errs)

    por["MS"]["fonte_uf"] = "IBGE SIDRA média (proxy CUB)"
    errs2 = validate_cub_snapshot(
        {"por_uf": por, "data_coleta": "2026-07-13"},
        sinapi=None,
        hoje=date(2026, 8, 6),
        max_idade_meses=3,
    )
    assert not any("MS" in e and "atrasado" in e.lower() for e in errs2)


def test_fresh_synthetic_passes():
    por = _full_por_uf()
    errs = validate_cub_snapshot(
        {"por_uf": por, "data_coleta": "2026-07-13"},
        sinapi=None,
        hoje=date(2026, 8, 6),
        max_idade_meses=3,
    )
    assert errs == []


def test_abril_fails_under_3_month_gate():
    por = _full_por_uf(periodo="abril 2026")
    errs = validate_cub_snapshot(
        {"por_uf": por, "data_coleta": "2026-07-13"},
        sinapi=None,
        hoje=date(2026, 8, 6),
        max_idade_meses=3,
    )
    assert any("atrasado" in e.lower() for e in errs)


def test_real_golden_passes_age_after_julho_refresh():
    import json

    cub = json.loads((ROOT / "data/cub_pilot/cub_estadual_golden.json").read_text(encoding="utf-8"))
    errs = validate_cub_snapshot(cub, sinapi=None, hoje=date(2026, 8, 6), max_idade_meses=3)
    age_errs = [e for e in errs if "atrasado" in e.lower()]
    assert age_errs == [], age_errs
