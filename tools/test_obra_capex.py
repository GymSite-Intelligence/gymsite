"""Testes — árvore tipo_obra adaptação × bruta no CAPEX A4."""
from __future__ import annotations

import pytest

from tools.financial_tools import _calcular_capex_detalhado, calcular_viabilidade_3_cenarios
from tools.obra_capex import (
    FATOR_OBRA_BRUTA,
    FATOR_OBRA_ADAPTACAO,
    normalize_tipo_obra,
    obra_m2_por_modelo,
)
from tools.obra_regua import resolve_capex_indices_for_uf


def test_normalize_tipo_obra_aliases():
    assert normalize_tipo_obra(None) == "adaptacao"
    assert normalize_tipo_obra("shell") == "bruta"
    assert normalize_tipo_obra("ADAPTACAO") == "adaptacao"


def test_bruta_m2_maior_que_adaptacao_ce():
    block = resolve_capex_indices_for_uf("CE")
    assert block is not None
    adapt = obra_m2_por_modelo("mid", tipo_obra="adaptacao", capex_indices=block)
    bruta = obra_m2_por_modelo("mid", tipo_obra="bruta", capex_indices=block)
    assert bruta > adapt
    cub = float(block["cub_m2"])
    assert adapt == pytest.approx(cub * FATOR_OBRA_ADAPTACAO, abs=0.05)
    assert bruta == pytest.approx(cub * FATOR_OBRA_BRUTA, abs=0.05)


def test_fortaleza_1250_adaptacao_vs_bruta():
    out_ad = calcular_viabilidade_3_cenarios(
        area_m2=1250.0,
        aluguel_mensal=20000.0,
        bairro="Meireles",
        cidade="Fortaleza",
        uf="CE",
        tipo_obra="adaptacao",
    )
    out_br = calcular_viabilidade_3_cenarios(
        area_m2=1250.0,
        aluguel_mensal=20000.0,
        bairro="Meireles",
        cidade="Fortaleza",
        uf="CE",
        tipo_obra="bruta",
    )
    cap_ad = out_ad["cenarios"]["mid"]["capex_detalhado"]
    cap_br = out_br["cenarios"]["mid"]["capex_detalhado"]
    assert cap_ad["tipo_obra"] == "adaptacao"
    assert cap_br["tipo_obra"] == "bruta"
    assert cap_br["linha_obra"] == "obra_bruta"
    assert cap_br["obra_adaptacao"] > cap_ad["obra_adaptacao"]
    assert "fator 0.58" in cap_br["fonte_obra_adaptacao"]


def test_capex_detalhado_default_adaptacao_inalterado():
    cap = _calcular_capex_detalhado(1250.0, "mid", uf_destino="CE")
    assert cap["tipo_obra"] == "adaptacao"
    assert cap["linha_obra"] == "obra_adaptacao"


def test_reforco_estrutural_emite_alerta():
    out = calcular_viabilidade_3_cenarios(
        area_m2=1250.0,
        aluguel_mensal=20000.0,
        bairro="Centro",
        cidade="Fortaleza",
        uf="CE",
        necessita_reforco_estrutural=True,
    )
    assert any("reforço estrutural" in a.lower() for a in out.get("alertas_obra") or [])
