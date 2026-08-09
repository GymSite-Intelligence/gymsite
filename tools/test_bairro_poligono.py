# tools/test_bairro_poligono.py
from pathlib import Path

from tools.bairro_poligono import load_fixture_geojson, point_in_ring, resolver_bairro_poligono

FIX = Path("data/ibge_bairros/fixtures/coco_ce.geojson")


def test_point_inside_coco_fixture():
    polys = load_fixture_geojson(FIX)
    assert len(polys) == 1
    ring = polys[0]["ring"]
    assert point_in_ring(-38.482, -3.747, ring) is True


def test_point_outside_coco_fixture():
    ring = load_fixture_geojson(FIX)[0]["ring"]
    assert point_in_ring(-38.600, -3.900, ring) is False


def test_resolve_coco_sem_acento():
    store = load_fixture_geojson(FIX)
    hit = resolver_bairro_poligono(id_municipio="2304400", bairro="Coco", _store=store)
    assert hit is not None
    assert hit["fonte"] == "ibge_bairro"
    assert hit["nm_bairro"] == "Cocó"


def test_resolve_miss_returns_none():
    store = load_fixture_geojson(FIX)
    assert resolver_bairro_poligono(id_municipio="2304400", bairro="Meireles", _store=store) is None
    assert resolver_bairro_poligono(id_municipio="9999999", bairro="Coco", _store=store) is None
