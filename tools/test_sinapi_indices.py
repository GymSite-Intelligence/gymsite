"""Testes B3 — SINAPI via SIDRA (fixtures)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.sinapi_indices import (
    FATOR_OBRA_ADAPTACAO,
    _parse_sidra_rows,
    build_capex_snapshot,
    capex_indices_for_uf,
    obra_adaptacao_por_modelo,
    save_capex_snapshot,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sinapi" / "sidra_2296_sample.json"


def test_parse_sidra_rows():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rows = _parse_sidra_rows(payload)
    ufs = {r["uf"]: r["sinapi_custo_m2"] for r in rows}
    assert ufs["CE"] == 1830.51
    assert ufs["SP"] == 2100.0


def test_obra_adaptacao_from_sinapi():
    obra = obra_adaptacao_por_modelo(1830.51)
    assert obra["mid"] == round(1830.51 * FATOR_OBRA_ADAPTACAO, 2)


def test_build_and_load_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "tools.sinapi_indices.CACHE_PATH",
        tmp_path / "capex_indices.json",
    )
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    snap = build_capex_snapshot(_parse_sidra_rows(payload))
    save_capex_snapshot(snap)
    block = capex_indices_for_uf("CE")
    assert block["fonte_obra"].startswith("IBGE")
    assert block["obra_adaptacao_por_m2"] is not None
    assert block["obra_adaptacao_por_m2_por_modelo"]["mid"] == block["obra_adaptacao_por_m2"]


def test_financial_uses_capex_indices():
    from tools.financial_tools import _obra_por_m2_modelo

    block = {
        "obra_adaptacao_por_m2": 347.8,
        "obra_adaptacao_por_m2_por_modelo": {"low": 198.74, "mid": 347.8, "premium": 596.23},
    }
    assert _obra_por_m2_modelo("mid", capex_indices=block) == 347.8
    assert _obra_por_m2_modelo("low", capex_indices=block) == 198.74
