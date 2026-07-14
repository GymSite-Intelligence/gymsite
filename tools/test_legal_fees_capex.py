"""Testes — legal_fees_pilot wired no CAPEX A4."""
from __future__ import annotations

import pytest

from tools.financial_tools import _calcular_capex_detalhado, calcular_viabilidade_3_cenarios
from tools.legal_fees_loader import resolver_taxas_capex


def test_resolver_taxas_fortaleza_mid():
    r = resolver_taxas_capex("Fortaleza", "CE", 1250.0, policy="mid")
    assert r is not None
    assert r["alvara_e_taxas"] == pytest.approx(473.88 + 800 + 400, abs=0.01)
    assert r["projeto_arquitetonico"] == pytest.approx(125000.0, abs=0.01)


def test_resolver_taxas_curitiba_projeto_escala():
    r = resolver_taxas_capex("Curitiba", "PR", 500.0, policy="mid")
    assert r is not None
    assert r["projeto_arquitetonico"] == pytest.approx(60000.0, abs=0.01)
    r2 = resolver_taxas_capex("Curitiba", "PR", 1250.0, policy="mid")
    assert r2["projeto_arquitetonico"] == pytest.approx(150000.0, abs=0.01)


def test_capex_detalhado_usa_legal_fees_fortaleza():
    ctx = resolver_taxas_capex("Fortaleza", "CE", 1250.0)
    cap = _calcular_capex_detalhado(1250.0, "mid", uf_destino="CE", legal_fees_ctx=ctx)
    assert cap["alvara_e_taxas"] != 8000.0
    assert cap["projeto_arquitetonico"] == pytest.approx(125000.0, abs=0.01)
    assert cap["legal_fees"] is not None
    assert "legal_fees_pilot" in cap["fonte_projeto_arquitetonico"] or "SEUMA" in cap["fonte_projeto_arquitetonico"]


def test_capex_detalhado_fallback_sem_piloto():
    cap = _calcular_capex_detalhado(1250.0, "mid", uf_destino="SP")
    assert cap["alvara_e_taxas"] == 8000.0
    assert cap["projeto_arquitetonico"] == 15000.0
    assert cap["legal_fees"] is None


def test_viabilidade_fortaleza_sem_alerta_legal():
    out = calcular_viabilidade_3_cenarios(
        area_m2=1250.0,
        aluguel_mensal=20000.0,
        bairro="Meireles",
        cidade="Fortaleza",
        uf="CE",
    )
    assert out.get("alertas_legal") == []
    mid = out["cenarios"]["mid"]["capex_detalhado"]
    assert mid["projeto_arquitetonico"] > 15000.0


def test_viabilidade_cidade_sem_piloto_emite_alerta():
    out = calcular_viabilidade_3_cenarios(
        area_m2=1250.0,
        aluguel_mensal=20000.0,
        bairro="Centro",
        cidade="Cidade Inexistente",
        uf="XX",
    )
    assert any("legal_fees_pilot" in a for a in out.get("alertas_legal") or [])
