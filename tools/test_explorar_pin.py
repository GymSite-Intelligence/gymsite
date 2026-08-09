"""Pin do Explorar: bairro (Cocó) não pode cair na orla / rio / parque."""
from __future__ import annotations

from tools.explorar_pin import (
    anexar_coords_sugestoes,
    filtrar_pins_nominatim,
    parse_lugar_explorar,
    resolver_explorar_pin,
)

_COCO_BAIRRO = {
    "placeId": "osm_relation_7032930",
    "bairro": "Cocó",
    "contexto": "Fortaleza, Ceará",
    "textoCompleto": "Cocó, Fortaleza, Ceará, Brasil",
    "lat": -3.7481588,
    "lng": -38.4808581,
    "osm_class": "boundary",
    "osm_type_tag": "administrative",
}
_RIO = {
    "placeId": "osm_relation_6969036",
    "bairro": "Rio Cocó",
    "contexto": "Fortaleza, Ceará",
    "textoCompleto": "Rio Cocó, Fortaleza, Ceará, Brasil",
    "lat": -3.8117117,
    "lng": -38.515192,
    "osm_class": "waterway",
    "osm_type_tag": "river",
}
_PARQUE = {
    "placeId": "osm_relation_6992908",
    "bairro": "Parque Estadual do Cocó",
    "contexto": "Fortaleza, Ceará",
    "textoCompleto": "Parque Estadual do Cocó, Fortaleza, Ceará, Brasil",
    "lat": -3.7656576,
    "lng": -38.4686572,
    "osm_class": "leisure",
    "osm_type_tag": "park",
}
_ORLA = {
    "placeId": "fake_orla",
    "bairro": "Cocó",
    "contexto": "Fortaleza, Ceará",
    "textoCompleto": "Av. Presidente Castelo Branco",
    "lat": -3.722,
    "lng": -38.505,
    "osm_class": "highway",
    "osm_type_tag": "primary",
}


def test_filtra_rio_parque_e_orla():
    out = filtrar_pins_nominatim([_RIO, _PARQUE, _ORLA, _COCO_BAIRRO], q="Cocó")
    assert [x["placeId"] for x in out] == ["osm_relation_7032930"]


def test_query_parque_mantem_parque():
    out = filtrar_pins_nominatim([_PARQUE, _COCO_BAIRRO], q="Parque do Cocó")
    assert any("parque" in (x["bairro"] or "").lower() for x in out)


def test_places_sem_lat_herda_coords_do_bairro_osm():
    places = [
        {
            "placeId": "ChIJ_fake",
            "bairro": "Cocó",
            "contexto": "Fortaleza - CE, Brasil",
            "textoCompleto": "Cocó, Fortaleza, Ceará, Região Nordeste, Brasil",
        }
    ]
    out = anexar_coords_sugestoes(places, [_RIO, _COCO_BAIRRO])
    assert out[0]["lat"] == _COCO_BAIRRO["lat"]
    assert out[0]["lng"] == _COCO_BAIRRO["lng"]
    assert -3.76 <= out[0]["lat"] <= -3.73
    assert -38.51 <= out[0]["lng"] <= -38.46


def test_filtra_mantem_bairro_bessa_suburb():
    bessa = {
        "placeId": "osm_rel_bessa",
        "bairro": "Bessa",
        "contexto": "João Pessoa, Paraíba",
        "textoCompleto": "Bessa, João Pessoa, Paraíba, Brasil",
        "lat": -7.078,
        "lng": -34.833,
        "osm_class": "place",
        "osm_type_tag": "suburb",
    }
    out = filtrar_pins_nominatim([bessa], q="Bessa")
    assert [x["placeId"] for x in out] == ["osm_rel_bessa"]


def test_parse_lugar_coco_fortaleza():
    lugar = parse_lugar_explorar("Cocó, Fortaleza, Ceará, Região Nordeste, Brasil")
    assert lugar["bairro"] == "Cocó"
    assert lugar["cidade"] == "Fortaleza"
    assert lugar["uf"] == "CE"


def test_resolve_coco_usa_centroide_ibge():
    pin = resolver_explorar_pin("Cocó, Fortaleza, Ceará, Região Nordeste, Brasil")
    assert pin is not None
    assert pin["fonte"] == "ibge_bairro_centroide"
    assert pin["lat"] < -3.73, "orla (~-3.72) não é o bairro Cocó"
    assert -3.76 <= pin["lat"] <= -3.73
    assert -38.51 <= pin["lng"] <= -38.46
