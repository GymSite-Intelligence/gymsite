"""Testes — bairro-renda via CKAN (inversão IDH-Renda + ordem de fontes). Sem rede."""
from __future__ import annotations

import math

import tools.bairro_renda_loader as m


def test_inversao_idhrenda_monotonica_e_ancorada():
    # Fórmula Atlas: IDH-Renda=0 → Rmin; =1 → Rmax; monotônica.
    assert abs(m._idhrenda_para_renda_pc(0.0) - m._ATLAS_RENDA_MIN) < 0.01
    assert abs(m._idhrenda_para_renda_pc(1.0) - m._ATLAS_RENDA_MAX) < 0.01
    assert m._idhrenda_para_renda_pc(0.30) < m._idhrenda_para_renda_pc(0.89)


def test_inversao_bate_formula_atlas():
    idh = 0.8935
    esperado = math.exp(
        idh * (math.log(m._ATLAS_RENDA_MAX) - math.log(m._ATLAS_RENDA_MIN))
        + math.log(m._ATLAS_RENDA_MIN)
    )
    assert abs(m._idhrenda_para_renda_pc(idh) - round(esperado, 2)) < 0.5


def test_enrich_usa_ckan_quando_disponivel(monkeypatch):
    catalogo = {
        "bairros": {"coco": {
            "idh_renda": 0.89, "renda_media_per_capita": 2095.2,
            "idh": 0.76, "ranking_idh": "6º",
        }},
        "cfg": m._CKAN_DATASETS["fortaleza_ce"],
    }
    monkeypatch.setattr(m, "_renda_bairro_ibge", lambda c, u, b: None)  # força path CKAN
    monkeypatch.setattr(m, "_carregar_ckan_bairros", lambda c, u: catalogo)
    out = m.enrich_demografia_bairro({}, "Fortaleza", "Cocó", "CE")["bairro"]
    assert out["renda_media"] == 2095.2
    assert out["idh_renda"] == 0.89 and out["ranking_idh"] == "6º"
    assert "CKAN" in out["fonte"]
    assert out["data_referencia"] == "2010"


def test_fallback_piloto_quando_ckan_vazio(monkeypatch):
    monkeypatch.setattr(m, "_renda_bairro_ibge", lambda c, u, b: None)  # força fallback
    monkeypatch.setattr(m, "_carregar_ckan_bairros", lambda c, u: None)
    monkeypatch.setattr(m, "load_pilot_catalog", lambda c, u: {
        "fonte": "bairro_renda_pilot", "data_referencia": "2024",
        "bairros": {"meireles": {"renda_media": 9000, "populacao": 37000}},
    })
    out = m.enrich_demografia_bairro({}, "Fortaleza", "Meireles", "CE")["bairro"]
    assert out["renda_media"] == 9000
    assert out["fonte"] == "bairro_renda_pilot"


def test_bairro_vazio_nao_quebra():
    out = m.enrich_demografia_bairro({}, "Fortaleza", "", "CE")["bairro"]
    assert out["granularidade"] == "bairro"
