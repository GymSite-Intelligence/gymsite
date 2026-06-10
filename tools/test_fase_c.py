"""Testes Fase C — franquias, legal fees, stale, alertas SMFT3."""
from __future__ import annotations

from tools.franchise_curated import bloco_para_bundle, redes_por_modelo
from tools.legal_fees_loader import bloco_para_bundle as legal_bloco
from tools.market_bundle import compute_bundle_stale


def test_franchise_catalog():
    bloco = bloco_para_bundle()
    assert len(bloco.get("redes") or []) >= 3
    low = redes_por_modelo("low")
    assert any(r.get("nome") == "Smart Fit" for r in low)


def test_legal_fees_fortaleza():
    legal = legal_bloco("Fortaleza", "CE")
    assert legal["disponivel"] is True
    assert legal["taxas"]["alvara_funcionamento_brl"]["min"] > 0


def test_legal_fees_missing_city():
    legal = legal_bloco("Cidade Inexistente", "XX")
    assert legal["disponivel"] is False


def test_compute_bundle_stale_fresh():
    bundle = {
        "gerado_em": "2099-01-01T00:00:00+00:00",
        "sector_benchmarks": {
            "empresas": [
                {
                    "ticker": "SMFT3",
                    "fonte": "CVM ITR",
                    "kpis": {"margem_ebitda_pct": 40.0},
                }
            ]
        },
        "capex_indices": {"fonte_obra": "IBGE SIDRA SINAPI tabela 2296"},
        "competicao_local": {"status": "ok"},
        "aluguel_portais": {"n_validos": 5},
    }
    stale, reasons = compute_bundle_stale(bundle)
    assert stale is False
    assert reasons == []


def test_compute_bundle_stale_degraded():
    bundle = {
        "gerado_em": "2099-01-01T00:00:00+00:00",
        "sector_benchmarks": {"empresas": [{"ticker": "SMFT3", "fonte": "CVM ITR", "kpis": {}}]},
        "capex_indices": {"fonte_obra": "benchmark_fixo_fase_a"},
        "competicao_local": {"status": "erro"},
        "aluguel_portais": {},
    }
    stale, reasons = compute_bundle_stale(bundle)
    assert stale is True
    assert "cvm_smft3_incompleto" in reasons
    assert "sinapi_fallback" in reasons


def test_alertas_sector_listed(monkeypatch):
    from tools import cvm_listed_metrics
    from tools import financial_tools as ft

    monkeypatch.setattr(
        cvm_listed_metrics,
        "kpis_smart_fit",
        lambda: {"margem_ebitda_pct": 40.0, "divida_liquida_ebitda": 2.0},
    )
    cenarios = {
        "mid": {"margem_percentual": 10.0, "payback_meses": 55},
    }
    alertas = ft._alertas_vs_sector_listed(cenarios)
    assert any("SMFT3" in a for a in alertas)


def test_airflow_dag_file_parses():
    import ast
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scripts" / "batch" / "dags" / "gym_market_weekly_dag.py"
    ast.parse(path.read_text(encoding="utf-8"))
