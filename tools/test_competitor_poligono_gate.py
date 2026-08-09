# tools/test_competitor_poligono_gate.py
from tools.bairro_poligono import load_fixture_geojson, resolver_bairro_poligono
from tools.competitor_tools import _places_para_concorrentes_bairro


def test_place_dentro_1km_mas_fora_poligono_excluido():
    hit = resolver_bairro_poligono(
        id_municipio="2304400",
        bairro="Coco",
        _store=load_fixture_geojson("data/ibge_bairros/fixtures/coco_ce.geojson"),
    )
    # Outside fixture box (-38.500..-38.460), ~east of centroid
    places = [{
        "displayName": {"text": "Gym Fora"},
        "formattedAddress": "x",
        "location": {"latitude": -3.747, "longitude": -38.520},
        "types": ["gym"],
        "businessStatus": "OPERATIONAL",
        "id": "p1",
    }]
    out = _places_para_concorrentes_bairro(
        places, query="q", bairro="Coco",
        lat_centro=-3.747, lng_centro=-38.482,
        raio_metros=1000, ring=hit["ring"],
    )
    assert out == []


def test_place_longe_mas_dentro_poligono_incluido():
    hit = resolver_bairro_poligono(
        id_municipio="2304400",
        bairro="Coco",
        _store=load_fixture_geojson("data/ibge_bairros/fixtures/coco_ce.geojson"),
    )
    places = [{
        "displayName": {"text": "Gym Dentro"},
        "formattedAddress": "x",
        "location": {"latitude": -3.745, "longitude": -38.490},
        "types": ["gym"],
        "businessStatus": "OPERATIONAL",
        "id": "p2",
    }]
    out = _places_para_concorrentes_bairro(
        places, query="q", bairro="Coco",
        lat_centro=-3.747, lng_centro=-38.482,
        raio_metros=100,  # would exclude by radius (~0.9 km away)
        ring=hit["ring"],
    )
    assert len(out) == 1
    assert out[0]["gate_espacial"] == "poligono_ibge_bairro"
