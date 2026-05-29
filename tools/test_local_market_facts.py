"""Testes — inferência de marcas e fatos locais OSM."""
from tools.local_market_facts import inferir_redes_de_concorrentes


def test_inferir_redes_smartfit_selfit():
    conc = [
        {"nome": "Smart Fit - Meireles"},
        {"nome": "Selfit Academias"},
        {"nome": "Agitate Cross"},
    ]
    redes = inferir_redes_de_concorrentes(conc)
    assert "Smart Fit" in redes
    assert "Selfit" in redes
    assert "Agitate" not in redes


def test_inferir_vazio():
    assert inferir_redes_de_concorrentes([]) == []
