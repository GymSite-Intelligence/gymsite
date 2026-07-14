"""Testes — régua CUB estadual no CAPEX A4."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.cub_indices import cub_indices_for_uf
from tools.financial_tools import _calcular_capex_detalhado, _obra_por_m2_modelo
from tools.obra_regua import carimbo_obra_adaptacao, obra_regua_policy, resolve_capex_indices_for_uf
from tools.sinapi_indices import FATOR_OBRA_ADAPTACAO, build_capex_snapshot, save_capex_snapshot

SINAPI_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sinapi" / "sidra_2296_sample.json"


def test_cub_indices_ce_mid():
    block = cub_indices_for_uf("CE")
    assert block["regua"] == "cub"
    assert block["cub_m2"] == pytest.approx(1969.47, abs=0.01)
    assert block["obra_adaptacao_por_m2"] == pytest.approx(1969.47 * FATOR_OBRA_ADAPTACAO, abs=0.01)


def test_resolve_default_regua_cub():
    assert obra_regua_policy() == "cub"
    block = resolve_capex_indices_for_uf("PR")
    assert block is not None
    assert block["regua"] == "cub"
    assert block["cub_m2"] == pytest.approx(2224.42, abs=0.01)


def test_capex_detalhado_uses_cub_regua():
    block = resolve_capex_indices_for_uf("CE")
    cap = _calcular_capex_detalhado(
        1250.0, "mid", uf_destino="CE", capex_indices=block
    )
    obra_m2 = block["obra_adaptacao_por_m2"]
    assert cap["obra_adaptacao"] == pytest.approx(obra_m2 * 1250.0, abs=1.0)
    assert cap["obra_adaptacao_por_m2"] == pytest.approx(obra_m2, abs=0.01)
    assert "CUB" in cap["fonte_obra_adaptacao"]


def test_carimbo_cites_cub_periodo():
    block = cub_indices_for_uf("CE")
    stamp = carimbo_obra_adaptacao(block, block["obra_adaptacao_por_m2"], "mid")
    assert "1969.47" in stamp
    assert "junho 2026" in stamp
    assert "fator 0.19" in stamp


def test_sinapi_regua_when_env_set(monkeypatch, tmp_path):
    monkeypatch.setenv("OBRA_REGUA", "sinapi")
    assert obra_regua_policy() == "sinapi"

    from tools.sinapi_indices import _parse_sidra_rows

    monkeypatch.setattr(
        "tools.sinapi_indices.CACHE_PATH",
        tmp_path / "capex_indices.json",
    )
    payload = json.loads(SINAPI_FIXTURE.read_text(encoding="utf-8"))
    snap = build_capex_snapshot(_parse_sidra_rows(payload))
    save_capex_snapshot(snap)

    block = resolve_capex_indices_for_uf("CE")
    assert block["regua"] == "sinapi"
    assert block["sinapi_custo_m2"] == pytest.approx(1830.51, abs=0.01)
    assert _obra_por_m2_modelo("mid", capex_indices=block) == pytest.approx(347.8, abs=0.1)


def test_cub_fallback_sinapi_when_uf_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("OBRA_REGUA", "cub")
    monkeypatch.setattr(
        "tools.cub_indices.GOLDEN_PATH",
        tmp_path / "empty_cub.json",
    )
    monkeypatch.setattr("tools.cub_indices.CACHE_PATH", tmp_path / "no_cache.json")

    from tools.sinapi_indices import _parse_sidra_rows

    monkeypatch.setattr(
        "tools.sinapi_indices.CACHE_PATH",
        tmp_path / "capex_indices.json",
    )
    payload = json.loads(SINAPI_FIXTURE.read_text(encoding="utf-8"))
    snap = build_capex_snapshot(_parse_sidra_rows(payload))
    save_capex_snapshot(snap)

    block = resolve_capex_indices_for_uf("CE")
    assert block["regua"] == "sinapi"
    assert block.get("regua_fallback") == "cub→sinapi"
