"""Testes Apêndice D — anéis competitivos. Puro, sem rede."""
from __future__ import annotations

from tools.aneis_competitivos_tools import (
    classificar_anel,
    classificar_porte,
    eh_multiesporte,
    enriquecer_competidores_aneis,
    resumo_aneis,
)

# Centroide do bairro alvo (Aldeota/Fortaleza aprox).
_LAT, _LNG = -3.737, -38.500
_ALVO = "Aldeota"


def test_no_bairro_por_nome():
    c = {"nome": "Academia X", "bairro": "ALDEOTA", "lat": -3.90, "lng": -38.60}  # longe mas mesmo bairro
    anel, peso, _ = classificar_anel(c, _ALVO, _LAT, _LNG)
    assert anel == "NO_BAIRRO" and peso == 1.0


def test_fronteira_ate_2km():
    c = {"nome": "Y", "bairro": "Meireles", "lat": -3.745, "lng": -38.500}  # ~0.9km
    anel, peso, dist = classificar_anel(c, _ALVO, _LAT, _LNG)
    assert anel == "FRONTEIRA" and peso == 0.5 and dist < 2


def test_regional_acima_2km():
    c = {"nome": "Z", "bairro": "Centro", "lat": -3.764, "lng": -38.500}  # ~3km
    anel, peso, dist = classificar_anel(c, _ALVO, _LAT, _LNG)
    assert anel == "REGIONAL" and peso == 0.2 and dist > 2


def test_sem_coord_sem_match_regional():
    anel, peso, dist = classificar_anel({"nome": "W", "bairro": "Outro"}, _ALVO, None, None)
    assert anel == "REGIONAL" and dist is None


def test_porte_por_avaliacoes():
    assert classificar_porte(50) == "pequena"
    assert classificar_porte(300) == "media"
    assert classificar_porte(2000) == "grande"


def test_multiesporte_flag():
    assert eh_multiesporte({"nome": "Club Natação Cocó", "tipos": ["gym"]}) is True
    assert eh_multiesporte({"nome": "Box Jiu Fight", "tipos": ["gym"]}) is True
    assert eh_multiesporte({"nome": "Smart Fit", "tipos": ["gym"]}) is False
    assert eh_multiesporte({"nome": "Natação X", "tipos": ["store"]}) is False  # não é gym


def test_resumo_score_ponderado_corrige_vizinho():
    comps = [
        {"nome": "A", "bairro": "Aldeota", "lat": -3.737, "lng": -38.500, "num_avaliacoes": 800},
        {"nome": "B", "bairro": "Meireles", "lat": -3.745, "lng": -38.500},   # fronteira
        {"nome": "C", "bairro": "Centro", "lat": -3.764, "lng": -38.500},     # regional
    ]
    enr = enriquecer_competidores_aneis(comps, _ALVO, _LAT, _LNG)
    r = resumo_aneis(enr)
    assert r["concorrentes_no_bairro"] == 1
    # score ponderado 1.0 + 0.5 + 0.2 = 1.7 (NÃO 3 da lista plana)
    assert abs(r["score_competitivo_ponderado"] - 1.7) < 0.01
    assert r["no_bairro_por_porte"]["grande"] == 1
