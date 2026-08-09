"""Gate de área do anteprojeto: mediana da faixa de porte (não escala de 300 m²)."""
from __future__ import annotations

import math

from tools.floor_plan_layout import (
    PORTE_FAIXAS_M2,
    _dimensoes,
    resolver_area_calculo,
)


def test_faixa_m_mediana_1150():
    """Canônico A4/consultor: M 800–1500 → mediana 1150."""
    r = resolver_area_calculo(1400.0)
    assert r["tamanho_preset"] == "m"
    assert r["area_m2_min"] == 800
    assert r["area_m2_max"] == 1500
    assert r["area_calculo_m2"] == 1150.0
    assert r["area_informada_m2"] == 1400.0
    assert r["metodo"] == "mediana_faixa_porte"


def test_faixa_m_borda_800():
    r = resolver_area_calculo(800.0)
    assert r["tamanho_preset"] == "m"
    assert r["area_calculo_m2"] == 1150.0


def test_faixa_p_mediana():
    r = resolver_area_calculo(600.0)
    assert r["tamanho_preset"] == "p"
    lo, hi = PORTE_FAIXAS_M2["p"]
    assert r["area_calculo_m2"] == round((lo + hi) / 2, 1)


def test_dimensoes_usam_mediana_nao_area_informada():
    """Envelope 4:3 sobre a mediana da faixa, não sobre 1400 nem 300."""
    gate = resolver_area_calculo(1400.0)
    w, h = _dimensoes(gate["area_calculo_m2"], 0.0, 0.0)
    expected_w = round(math.sqrt(1150.0 * 4.0 / 3.0), 2)
    expected_h = round(1150.0 / expected_w, 2)
    assert w == expected_w
    assert h == expected_h
    # Não deve coincidir com envelope de 1400 nem de 300
    w1400, _ = _dimensoes(1400.0, 0.0, 0.0)
    w300, _ = _dimensoes(300.0, 0.0, 0.0)
    assert w != w1400
    assert w != w300


def test_dimensoes_explicitas_preservadas():
    w, h = _dimensoes(1400.0, comprimento_m=40.0, largura_m=35.0)
    assert (w, h) == (40.0, 35.0)
