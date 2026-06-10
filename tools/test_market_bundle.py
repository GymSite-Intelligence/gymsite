"""Testes market_bundle e CKAN (sem rede quando mockado)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from tools.market_bundle import (
    bundle_is_fresh,
    bundle_to_briefing_md,
    carregar_market_bundle,
    save_market_bundle,
    load_market_bundle,
)


@pytest.fixture
def sample_bundle():
    now = datetime.now(timezone.utc).isoformat()
    return {
        "version": "1.0",
        "gerado_em": now,
        "local": {"cidade": "Fortaleza", "bairro": "Meireles", "uf": "CE"},
        "demografia": {
            "municipio": {
                "populacao_total": 2428678,
                "renda_media_domiciliar": 1572,
                "fonte": "IBGE",
                "renda_granularidade": "municipal",
            },
            "bairro": {"renda_media": None, "fonte": None},
        },
        "competicao_local": {
            "status": "ok",
            "total_unidades_osm": 10,
            "redes_detectadas_osm": ["Smart Fit"],
        },
        "aluguel_portais": {"n_validos": 5, "mediana_r_m2": 26.0, "confianca": "alta"},
        "bcb_imobiliario": {"ok": True, "fonte": "BCB"},
        "sector_benchmarks": {"empresas": [{"nome": "Smart Fit", "ticker": "SMFT3", "kpis": {}}]},
        "missing_fields": ["renda_media_bairro"],
        "stale": False,
    }


def test_bundle_fresh_and_briefing(sample_bundle, tmp_path, monkeypatch):
    monkeypatch.setattr("tools.market_bundle.BUNDLE_DIR", tmp_path)
    save_market_bundle("Fortaleza", "Meireles", "CE", sample_bundle)
    loaded = load_market_bundle("Fortaleza", "Meireles", "CE")
    assert loaded is not None
    assert bundle_is_fresh(loaded)
    md = bundle_to_briefing_md(loaded)
    assert "Smart Fit" in md
    assert "renda_media_bairro" in md or "bairro" in md.lower()
    out = carregar_market_bundle("Fortaleza", "Meireles", "CE")
    assert "market_bundle" in out
    assert "status=missing" not in out


def test_carregar_missing(monkeypatch, tmp_path):
    monkeypatch.setattr("tools.market_bundle.BUNDLE_DIR", tmp_path)
    out = carregar_market_bundle("X", "Y", "ZZ")
    assert "status=missing" in out


def test_inject_skip_deep_research(sample_bundle, tmp_path, monkeypatch):
    monkeypatch.setattr("tools.market_bundle.BUNDLE_DIR", tmp_path)
    save_market_bundle("Fortaleza", "Meireles", "CE", sample_bundle)
    from tools.market_bundle import inject_market_bundle_context

    ctx = inject_market_bundle_context("Fortaleza", "Meireles", "CE", {})
    assert ctx.get("market_bundle_fresh") is True
    assert "market_bundle_briefing_md" in ctx
    assert ctx.get("market_bundle_partial") is True  # missing_fields non-empty
