"""Testes — piloto legal_fees 15 cidades."""
from __future__ import annotations

import pytest

from tools.legal_fees_loader import (
    PILOT_CITIES,
    _slug,
    list_pilot_cities,
    load_legal_fees,
    load_manifest,
    resolver_taxas_capex,
)


def test_slug_ascii_sem_acento():
    assert _slug("São Paulo", "SP") == "sao_paulo_sp"
    assert _slug("Brasília", "DF") == "brasilia_df"
    assert _slug("Niterói", "RJ") == "niteroi_rj"
    assert _slug("Fortaleza", "CE") == "fortaleza_ce"


def test_manifest_15_cidades():
    manifest = load_manifest()
    cidades = manifest.get("cidades") or []
    assert len(cidades) == 15
    assert len(PILOT_CITIES) == 15


@pytest.mark.parametrize("cidade,uf", PILOT_CITIES)
def test_pilot_json_existe(cidade: str, uf: str):
    data = load_legal_fees(cidade, uf)
    assert data is not None, f"missing JSON for {cidade}/{uf}"
    assert data.get("cidade") == cidade
    assert (data.get("uf") or "").upper() == uf
    taxas = data.get("taxas") or {}
    assert taxas.get("alvara_funcionamento_brl")
    assert taxas.get("projeto_arquitetonico_cau_brl")


def test_list_pilot_cities_slugs():
    rows = list_pilot_cities()
    assert len(rows) == 15
    slugs = {r["slug"] for r in rows}
    assert "sao_paulo_sp" in slugs
    assert "fortaleza_ce" in slugs


def test_resolver_sao_paulo_mid_1250():
    r = resolver_taxas_capex("São Paulo", "SP", 1250.0, policy="mid")
    assert r is not None
    assert r["alvara_e_taxas"] != 8000.0
    assert r["projeto_arquitetonico"] == pytest.approx(162500.0, abs=1.0)


def test_fortaleza_curitiba_nao_revisao_pendente():
    for cidade, uf in (("Fortaleza", "CE"), ("Curitiba", "PR")):
        data = load_legal_fees(cidade, uf)
        assert data is not None
        assert not data.get("revisao_pendente")
