"""Testes CVM / sector_listed snapshot."""
from __future__ import annotations

import json

import pytest

from tools.cvm_listed_metrics import (
    DEFAULT_LISTED,
    empresa_por_ticker,
    merge_into_benchmark_snapshot,
    obter_sector_listed,
    save_sector_listed_snapshot,
)


def test_obter_sector_listed_defaults():
    data = obter_sector_listed(force_defaults=True)
    assert data.get("empresas")
    assert empresa_por_ticker("SMFT3") is not None
    tickers = [e.get("ticker") for e in data.get("empresas") or []]
    assert "BIOM3" not in tickers


def test_save_and_load_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.cvm_listed_metrics.CACHE_PATH", tmp_path / "sector.json")
    save_sector_listed_snapshot(DEFAULT_LISTED)
    loaded = obter_sector_listed()
    assert loaded.get("version") == "1.1"
    assert json.loads((tmp_path / "sector.json").read_text(encoding="utf-8"))["empresas"]


def test_merge_into_benchmark_snapshot():
    snap = merge_into_benchmark_snapshot({"setorial": {"ticket_por_modelo": {"low": 79}}})
    assert "sector_listed" in snap
    assert snap["setorial"]["ticket_por_modelo"]["low"] == 79
