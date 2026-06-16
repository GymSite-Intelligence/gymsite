"""Testes bairro_renda_loader (piloto Fortaleza)."""
from __future__ import annotations

import tools.bairro_renda_loader as m
from tools.bairro_renda_loader import enrich_demografia_bairro, load_pilot_catalog


def test_pilot_meireles(monkeypatch):
    # Força o path piloto: desliga IBGE 2022 (renda_bairro) e CKAN, que têm precedência.
    monkeypatch.setattr(m, "_renda_bairro_ibge", lambda c, u, b: None)
    monkeypatch.setattr(m, "_carregar_ckan_bairros", lambda c, u: None)
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
