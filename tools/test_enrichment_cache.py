"""Testes do hook de cache de enrichment no pipeline."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tools.enrichment_cache import (
    CACHE_DIR,
    cache_is_fresh,
    inject_cache_context,
    load_cache_file,
    reset_pipeline_enrichment_context,
    set_pipeline_enrichment_context,
    should_skip_tool,
    cached_competicao_local,
)


@pytest.fixture
def sample_cache(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.enrichment_cache.CACHE_DIR", tmp_path)
    data = {
        "cache_key": "abc123",
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "local": {"cidade": "Fortaleza", "bairro": "Meireles", "uf": "CE"},
        "competicao_local": {
            "status": "ok",
            "total_unidades_osm": 25,
            "redes_detectadas_osm": ["Selfit", "Smart Fit"],
        },
        "competicao_osm_unidades": 25,
        "redes_detectadas_osm": ["Selfit", "Smart Fit"],
        "aluguel_portais": {"n_validos": 10, "mediana_r_m2": 26.0, "tier1_suficiente": True},
        "bcb_imobiliario": {"ok": True, "fonte": "BCB"},
    }
    path = tmp_path / "fortaleza_meireles_ce.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return data


def test_cache_is_fresh_true(sample_cache):
    assert cache_is_fresh(sample_cache) is True


def test_cache_is_fresh_false_when_stale(sample_cache):
    old = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    sample_cache["gerado_em"] = old
    assert cache_is_fresh(sample_cache) is False


def test_inject_cache_context_sets_skip_when_fresh(sample_cache, monkeypatch):
    monkeypatch.setattr(
        "tools.enrichment_cache.compress_from_cache",
        lambda d: "RESUMO",
    )
    ctx = inject_cache_context("Fortaleza", "Meireles", "CE", {})
    assert ctx["local_market_summary"] == "RESUMO"
    assert ctx["cache_key"] == "abc123"
    assert "local_market_facts" in ctx.get("skip_tools", [])
    assert ctx["enrichment_cache_fresh"] is True


def test_should_skip_tool_with_contextvar(sample_cache):
    ctx = {
        "enrichment_cache_fresh": True,
        "skip_tools": ["local_market_facts"],
        "enrichment_cache": sample_cache,
    }
    token = set_pipeline_enrichment_context(ctx)
    try:
        assert should_skip_tool("local_market_facts") is True
        assert should_skip_tool("other") is False
        hit = cached_competicao_local()
        assert hit is not None
        assert hit["total_unidades_osm"] == 25
    finally:
        reset_pipeline_enrichment_context(token)


def test_load_cache_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.enrichment_cache.CACHE_DIR", tmp_path)
    assert load_cache_file("X", "Y", "ZZ") is None


def test_load_cache_file_real_meireles():
    if not (CACHE_DIR / "fortaleza_meireles_ce.json").is_file():
        pytest.skip("cache de producao ausente")
    data = load_cache_file("Fortaleza", "Meireles", "CE")
    assert data is not None
    assert data.get("competicao_osm_unidades") or (
        (data.get("competicao_local") or {}).get("total_unidades_osm")
    )
