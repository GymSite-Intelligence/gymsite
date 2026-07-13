"""Testes Fase C — franquias, legal fees, stale, alertas SMFT3."""
from __future__ import annotations

from tools.franchise_curated import bloco_para_bundle, redes_por_modelo
from tools.legal_fees_loader import bloco_para_bundle as legal_bloco
from tools.market_bundle import (
    LIVE_TRAIL_FIELDS,
    compute_bundle_stale,
    inject_market_bundle_context,
    live_trail_pending,
)


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


def test_competicao_ausente_nao_marca_stale():
    """Trilha viva: competição faltando NÃO degrada bundle batch (aluguel = A4 MRLR)."""
    bundle = {
        "gerado_em": "2099-01-01T00:00:00+00:00",
        "sector_benchmarks": {
            "empresas": [{"ticker": "SMFT3", "fonte": "CVM ITR", "kpis": {"margem_ebitda_pct": 40.0}}]
        },
        "capex_indices": {"fonte_obra": "IBGE SIDRA SINAPI tabela 2296"},
        "competicao_local": {"status": "erro", "motivo": "GOOGLE_MAPS_API_KEY ausente"},
        "aluguel_portais": {},
    }
    stale, reasons = compute_bundle_stale(bundle)
    assert stale is False
    assert reasons == []
    assert set(live_trail_pending(bundle)) == {"competicao_osm"}


def test_inject_trilha_feliz_pula_dr_com_competicao_pendente(tmp_path, monkeypatch):
    """Bundle fresco + estrutura completa → skip_deep_research mesmo sem competição."""
    import json
    from tools import market_bundle as mb

    bundle = {
        "version": "1.0",
        "local": {"cidade": "X", "bairro": "y", "uf": "CE"},
        "gerado_em": "2099-01-01T00:00:00+00:00",
        "valido_ate": "2099-01-08T00:00:00+00:00",
        "demografia": {"municipio": {}, "bairro": {"renda_media": 5000}},
        "sector_benchmarks": {"empresas": []},
        "competicao_local": {"status": "erro"},
        "aluguel_portais": {"n_validos": 10},
        "missing_fields": ["competicao_osm"],
        "stale": False,
    }
    monkeypatch.setattr(mb, "BUNDLE_DIR", tmp_path)
    (tmp_path / "x_y_CE.json").write_text(json.dumps(bundle), encoding="utf-8")
    monkeypatch.delenv("A0_CONTEXT_SOURCE", raising=False)

    ctx = inject_market_bundle_context("X", "y", "CE", {})
    assert ctx["market_bundle_fresh"] is True
    assert ctx["skip_deep_research"] is True
    assert ctx["market_bundle_live_pending"] == ["competicao_osm"]
    assert "competicao_osm" in LIVE_TRAIL_FIELDS


def test_sector_kpi_coverage_parcial():
    from tools.cvm_listed_metrics import OPERATIONAL_KPIS, sector_kpi_coverage

    emp = {"ticker": "SMFT3", "kpis": {"alunos_ativos": 5_200_000, "arpu_brl": None,
                                        "churn_pct": None, "capex_por_unidade_brl": None}}
    cov = sector_kpi_coverage(emp)
    assert cov["total"] == len(OPERATIONAL_KPIS)
    assert cov["preenchidos"] == 1
    assert cov["pct"] == 25.0
    assert set(cov["faltando"]) == {"arpu_brl", "churn_pct", "capex_por_unidade_brl"}


def test_ri_overlay_preenche_so_nulos(monkeypatch):
    from tools import cvm_listed_metrics as cvm

    monkeypatch.setattr(cvm, "_load_snapshot", lambda: {
        "empresas": [{"ticker": "SMFT3", "fonte": "CVM ITR",
                      "kpis": {"margem_ebitda_pct": 47.8, "alunos_ativos": None, "arpu_brl": None}}]
    })
    monkeypatch.setattr(cvm, "_load_ri_overlay", lambda: {
        "fonte": "RI teste",
        "empresas": {"SMFT3": {"periodo_ref": "1T26",
                               "kpis": {"alunos_ativos": 5_200_000, "margem_ebitda_pct": 99.9}}},
    })
    data = cvm.obter_sector_listed()
    k = data["empresas"][0]["kpis"]
    assert k["alunos_ativos"] == 5_200_000      # null preenchido
    assert k["margem_ebitda_pct"] == 47.8        # CVM NÃO sobrescrito
    assert data["empresas"][0]["kpis_operacionais_periodo"] == "1T26"


def test_sector_kpi_alertas_flag(monkeypatch):
    from tools import cvm_listed_metrics as cvm

    parcial = {"empresas": [{"ticker": "SMFT3", "kpis": {"alunos_ativos": 1, "arpu_brl": None,
                                                          "churn_pct": None, "capex_por_unidade_brl": None}}]}
    assert any("operacionais" in a for a in cvm.sector_kpi_alertas(parcial))
    cheio = {"empresas": [{"ticker": "SMFT3", "kpis": {"alunos_ativos": 1, "arpu_brl": 1,
                                                       "churn_pct": 1, "capex_por_unidade_brl": 1}}]}
    assert cvm.sector_kpi_alertas(cheio) == []


def test_financial_alerta_operacional_parcial(monkeypatch):
    from tools import cvm_listed_metrics as cvm
    from tools import financial_tools as ft

    monkeypatch.setattr(cvm, "kpis_smart_fit",
                        lambda: {"margem_ebitda_pct": 40.0, "divida_liquida_ebitda": 2.0})
    monkeypatch.setattr(cvm, "empresa_por_ticker",
                        lambda t: {"ticker": "SMFT3", "kpis": {"alunos_ativos": 1, "arpu_brl": None,
                                                               "churn_pct": None, "capex_por_unidade_brl": None}})
    alertas = ft._alertas_vs_sector_listed({"mid": {"margem_percentual": 10.0, "payback_meses": 55}})
    assert any("operacional" in a.lower() for a in alertas)


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
