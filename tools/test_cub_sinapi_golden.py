"""Golden tests — CUB estadual × SINAPI (oscilação e estabilidade)."""
from __future__ import annotations

import pytest

from tools.cub_sinapi_compare import (
    aggregate_metrics,
    compare_all,
    compare_uf,
    format_report_md,
    load_expectations,
    rank_overlap,
    validate_against_golden,
)


def test_compare_uf_ce_golden():
    row = compare_uf("CE")
    assert row is not None
    assert row["cub_m2"] == 1969.47
    assert row["sinapi_m2"] == 1832.26
    assert row["ratio_cub_sinapi"] == pytest.approx(1.0749, abs=0.0001)
    assert row["obra_adaptacao_mid"] == pytest.approx(348.13, abs=0.1)


def test_compare_all_covers_27_ufs():
    rows = compare_all()
    assert len(rows) == 27


def test_aggregate_ratio_band_estavel():
    rows = compare_all()
    agg = aggregate_metrics(rows)
    assert agg["ratio_cub_sinapi_mean"] == pytest.approx(1.0621, abs=0.02)
    assert agg["ratio_cub_sinapi_stdev"] == pytest.approx(0.0095, abs=0.005)
    assert 1.04 <= agg["ratio_cub_sinapi_min"] <= 1.05
    assert 1.08 <= agg["ratio_cub_sinapi_max"] <= 1.09


def test_obra_pct_cub_estavel_entre_ufs():
    rows = compare_all()
    pcts = [r["obra_pct_cub"] for r in rows]
    assert min(pcts) >= 17.0
    assert max(pcts) <= 18.5
    assert aggregate_metrics(rows)["obra_pct_cub_mean"] == pytest.approx(17.9, abs=0.3)


def test_rank_top5_overlap_alto():
    rows = compare_all()
    rank = rank_overlap(rows, top_n=5)
    assert rank["overlap"] >= 4
    assert "SC" in rank["overlap_ufs"]
    assert "RJ" in rank["overlap_ufs"]


def test_validate_golden_states_passa():
    rows = compare_all()
    result = validate_against_golden(rows)
    assert result["ok"], result["failures"]


def test_piloto_ce_pr_dentro_tolerancia():
    exp = load_expectations()
    rows = compare_all(ufs=exp["ufs_piloto_produto"])
    result = validate_against_golden(rows, expectations=exp)
    assert result["ok"], result["failures"]


def test_format_report_md_tem_ancoras():
    md = format_report_md()
    assert "CE" in md and "PR" in md
    assert "CUB x SINAPI" in md
