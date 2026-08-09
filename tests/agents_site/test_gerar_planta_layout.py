"""gerar_planta_layout_zonas — archit-app SVG anteprojeto."""
from __future__ import annotations

import pytest

from agents_site.tools import gerar_planta_layout_zonas


archit_app = pytest.importorskip("archit_app")


def test_300m2_icarai_preset_tiles_and_svg():
    r = gerar_planta_layout_zonas(300.0)
    assert r.get("tipo") == "anteprojeto_nao_oficial"
    assert r.get("preset") == "musculacao_entrada_fundo"
    assert "erro" not in r
    assert len(r.get("zonas") or []) == 6
    assert (r.get("svg") or "").startswith("<?xml")
    assert r.get("svg_base64")
    dims = r["dimensoes_m"]
    assert dims["area_informada_m2"] == 300.0
    # 300 → faixa PP 200–500 → mediana 350 (gate A4, não área bruta)
    assert dims["area_calculo_m2"] == 350.0
    assert dims["tamanho_preset"] == "pp"
    assert dims["metodo_area"] == "mediana_faixa_porte"
    assert abs(dims["area_desenhada_m2"] - 350.0) < 2.0
    nomes = {z["nome"] for z in r["zonas"]}
    assert any("Halteres" in n for n in nomes)
    assert any("Racks" in n for n in nomes)
    assert "RRT" in (r.get("aviso") or "")
    assert "mediana" in (r.get("aviso") or "").lower()


def test_1400_usa_mediana_m_nao_area_bruta():
    r = gerar_planta_layout_zonas(1400.0)
    if "erro" in r:
        pytest.skip(r["erro"])
    dims = r["dimensoes_m"]
    assert dims["area_informada_m2"] == 1400.0
    assert dims["area_calculo_m2"] == 1150.0
    assert dims["tamanho_preset"] == "m"
    assert abs(dims["area_desenhada_m2"] - 1150.0) < 2.0


def test_dimensoes_explicitas():
    r = gerar_planta_layout_zonas(300.0, comprimento_m=20.0, largura_m=15.0)
    assert r["dimensoes_m"]["comprimento"] == 20.0
    assert r["dimensoes_m"]["largura"] == 15.0


def test_preset_invalido():
    r = gerar_planta_layout_zonas(100.0, preset="casa")
    assert "erro" in r


def test_sanitize_poll_strips_base64():
    from tools.floor_plan_layout import sanitize_planta_tool_result

    r = gerar_planta_layout_zonas(200.0)
    assert r.get("svg_base64")
    clean = sanitize_planta_tool_result(r)
    assert "svg_base64" not in clean
    assert clean.get("svg")
