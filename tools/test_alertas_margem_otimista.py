"""Alertas de plausibilidade A4 — TIR alta e VPL negativo."""

from tools.financial_tools import _alertas_margem_otimista


def test_alerta_vpl_negativo():
    cenarios = {
        "mid": {
            "modelo": "Mid-Market",
            "margem_percentual": 17.0,
            "tir_anual_pct": 12.0,
            "vpl_5_anos": -150_000.0,
        }
    }
    alertas = _alertas_margem_otimista(cenarios)
    assert any("VPL" in a and "negativo" in a.lower() for a in alertas), alertas


def test_alerta_tir_acima_100():
    cenarios = {
        "low": {
            "modelo": "Low-Cost",
            "margem_percentual": 30.0,
            "tir_anual_pct": 150.0,
            "vpl_5_anos": 50_000.0,
        }
    }
    alertas = _alertas_margem_otimista(cenarios)
    assert any("TIR" in a and "150" in a for a in alertas), alertas


def test_vpl_positivo_sem_alerta_vpl():
    cenarios = {
        "premium": {
            "modelo": "Premium",
            "margem_percentual": 22.0,
            "tir_anual_pct": 18.0,
            "vpl_5_anos": 80_000.0,
        }
    }
    alertas = _alertas_margem_otimista(cenarios)
    assert not any("VPL" in a for a in alertas), alertas
