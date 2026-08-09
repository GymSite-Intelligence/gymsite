# tools/test_demografia_poligono.py
from tools.bairro_poligono import load_fixture_geojson, resolver_bairro_poligono
from tools.censo_setor_tools import demografia_setor_poligono
from tools.perfil_sexo_idade_tools import perfil_sexo_idade_poligono

FIX_ROWS = [
    {
        "lat": -3.747, "lng": -38.482, "pessoas": 1000, "domicilios": 400,
        "h_total": 480, "m_total": 520, "h_15_24": 50, "m_15_24": 50,
        "h_25_39": 200, "m_25_39": 220, "h_40_59": 150, "m_40_59": 160,
        "h_60_mais": 80, "m_60_mais": 90,
    },
    {
        "lat": -3.900, "lng": -38.600, "pessoas": 5000, "domicilios": 2000,
        "h_total": 2500, "m_total": 2500, "h_15_24": 100, "m_15_24": 100,
        "h_25_39": 1000, "m_25_39": 1000, "h_40_59": 800, "m_40_59": 800,
        "h_60_mais": 600, "m_60_mais": 600,
    },
]


def test_pop_e_piramide_mesmo_n_setores():
    hit = resolver_bairro_poligono(
        id_municipio="2304400",
        bairro="Coco",
        _store=load_fixture_geojson("data/ibge_bairros/fixtures/coco_ce.geojson"),
    )
    ring = hit["ring"]
    pop = demografia_setor_poligono("2304400", ring, _rows=FIX_ROWS)
    pir = perfil_sexo_idade_poligono("2304400", ring, _rows=FIX_ROWS)
    assert pop["n_setores"] == 1
    assert pir["n_setores"] == 1
    assert pop["populacao"] == 1000
