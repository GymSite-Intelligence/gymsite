"""Testes bairro_renda_loader (piloto Fortaleza)."""
from __future__ import annotations

from tools.bairro_renda_loader import enrich_demografia_bairro, load_pilot_catalog


def test_pilot_meireles():
    pilot = load_pilot_catalog("Fortaleza", "CE")
    assert pilot is not None
    demo = enrich_demografia_bairro(
        {"municipio": {}, "bairro": {}},
        "Fortaleza",
        "Meireles",
        "CE",
    )
    b = demo["bairro"]
    assert b.get("renda_media") == 4850
    assert b.get("fonte")


def test_unknown_bairro_empty():
    demo = enrich_demografia_bairro(
        {"municipio": {}, "bairro": {}},
        "Fortaleza",
        "BairroInexistente",
        "CE",
    )
    assert demo["bairro"].get("renda_media") is None
