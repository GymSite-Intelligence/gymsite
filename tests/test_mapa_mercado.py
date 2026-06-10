"""Payload do mapa municipal — concorrentes (geo DB) + entrantes JSONB."""
from __future__ import annotations

from unittest.mock import patch

from tools.mapa_mercado import (
    _competidor_mapa_row,
    _filtrar_entrantes_mapa,
    _geocode_competidores,
    build_mapa_mercado_payload,
)


def test_competidor_mapa_row_usa_geo():
    row = _competidor_mapa_row(
        {
            "nome": "Smart Fit",
            "place_id": "ChIJ_x",
            "lat": -3.73,
            "lng": -38.52,
            "distancia_km": 1.2,
            "rating_oficial": 4.5,
            "google_maps_uri": "https://maps.example/x",
        }
    )
    assert row is not None
    assert row["nome"] == "Smart Fit"
    assert row["lat"] == -3.73
    assert row["rating"] == 4.5


def test_competidor_mapa_row_sem_coords_retorna_none():
    assert _competidor_mapa_row({"nome": "X", "lat": 0, "lng": 0}) is None


@patch("tools.mapa_mercado.geocode_endereco")
def test_geocode_competidores_preenche_endereco(mock_geo):
    mock_geo.return_value = {"lat": -21.17, "lng": -47.81}
    enriched, n = _geocode_competidores(
        [{"nome": "Gym", "endereco": "Rua A, 1, Cidade - SP"}]
    )
    assert n == 1
    assert enriched[0]["lat"] == -21.17
    assert enriched[0]["lng"] == -47.81
    mock_geo.assert_called_once()


def test_filtrar_entrantes_segmento_e_flag():
    raw = [
        {"cnpj": "1", "segmento_operacao": "academia"},
        {"cnpj": "2", "segmento_operacao": "restaurante"},
        {"cnpj": "3", "incluir_no_parque": False},
    ]
    out = _filtrar_entrantes_mapa(raw)
    assert len(out) == 1
    assert out[0]["cnpj"] == "1"


@patch("tools.mapa_mercado._geocode_competidores")
@patch("tools.mapa_mercado._geocode_entrantes")
@patch("tools.mapa_mercado._geocode_cidade")
def test_build_payload_concorrentes_e_bounds(mock_geo_cidade, mock_geo_ent, mock_geo_comp):
    mock_geo_comp.side_effect = lambda comps, **kw: (comps, 0)
    mock_geo_cidade.return_value = {
        "centro": {"lat": -3.7, "lng": -38.5},
        "bounds": {
            "ne": {"lat": -3.6, "lng": -38.4},
            "sw": {"lat": -3.8, "lng": -38.6},
        },
        "endereco": "Fortaleza, CE, Brasil",
    }
    mock_geo_ent.return_value = [
        {"cnpj": "99", "lat": -3.71, "lng": -38.51, "peso_heatmap": 0.9},
    ]

    payload = build_mapa_mercado_payload(
        cidade="Fortaleza",
        uf="CE",
        bairro="Aldeota",
        competidores=[
            {"nome": "Gym A", "lat": -3.72, "lng": -38.52, "rating_oficial": 4.0},
            {"nome": "Sem geo", "lat": None, "lng": None},
        ],
        entrantes_block={
            "entrantes": [{"cnpj": "99", "segmento_operacao": "academia"}],
        },
        site_lat=-3.715,
        site_lng=-38.505,
    )

    assert payload["cidade"] == "Fortaleza"
    assert len(payload["concorrentes"]) == 1
    assert payload["concorrentes"][0]["nome"] == "Gym A"
    assert len(payload["entrantes"]) == 1
    assert payload["bounds_municipio"]["ne"]["lat"] == -3.6
    assert payload["site"]["label"] == "Aldeota"


@patch("tools.mapa_mercado._geocode_competidores")
@patch("tools.mapa_mercado._geocode_entrantes")
@patch("tools.mapa_mercado._geocode_cidade")
def test_build_payload_bounds_fallback_pins(mock_geo_cidade, mock_geo_ent, mock_geo_comp):
    mock_geo_comp.side_effect = lambda comps, **kw: (comps, 0)
    mock_geo_cidade.return_value = {
        "centro": {"lat": -3.7, "lng": -38.5},
        "endereco": "Fortaleza, CE, Brasil",
    }
    mock_geo_ent.return_value = []

    payload = build_mapa_mercado_payload(
        cidade="Fortaleza",
        uf="CE",
        bairro="",
        competidores=[{"nome": "Gym", "lat": -3.72, "lng": -38.52}],
        entrantes_block=None,
    )

    b = payload["bounds_municipio"]
    assert b is not None
    assert b["ne"]["lat"] > b["sw"]["lat"]
    assert b["ne"]["lng"] > b["sw"]["lng"]


def test_mapa_mercado_route_registered():
    from api import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    routes = {(r.path, tuple(r.methods)) for r in app.routes if hasattr(r, "methods")}
    assert ("/api/relatorios/{relatorio_id}/mapa-mercado", ("GET",)) in routes
