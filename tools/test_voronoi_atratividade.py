"""TDD Voronoi smoke."""


def test_smoke_classic_scales_pool():
    from tools.voronoi_atratividade import compute_voronoi_smoke

    ring = [(-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0), (-1.0, -1.0)]
    sites = [
        {"lat": 0.0, "lng": -0.5, "peso": 1500.0, "is_candidato": True},
        {"lat": 0.0, "lng": 0.5, "peso": 1500.0, "is_candidato": False},
    ]
    setores = [
        {"lat": 0.0, "lng": -0.4, "pessoas": 800},
        {"lat": 0.0, "lng": 0.4, "pessoas": 200},
    ]
    out = compute_voronoi_smoke(
        sites=sites, ring=ring, setores=setores, pool_ref=1000, pop_bairro=1000
    )
    assert out["status"] == "ok"
    assert out["pop_celula"] == 800
    assert out["pool_ref"] == 1000
    assert out["pool_voronoi"] == 800
    assert out["metodo_pool"] == "escala_pop"
    assert out["delta_pct"] == -0.2
    assert out["pool_voronoi_ponderado"] is not None


def test_smoke_indisponivel_sem_candidato_coords():
    from tools.voronoi_atratividade import compute_voronoi_smoke

    out = compute_voronoi_smoke(
        sites=[{"lat": None, "lng": None, "peso": 1500, "is_candidato": True}],
        ring=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.0, 0.0)],
        setores=[],
        pool_ref=100,
        pop_bairro=100,
    )
    assert out["status"] == "indisponivel"
    assert out["motivo"] in ("sem_coords", "poucos_pontos")


def test_smoke_weighted_differs_when_pesos_skew():
    from tools.voronoi_atratividade import compute_voronoi_smoke

    ring = [(-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0), (-1.0, -1.0)]
    sites = [
        {"lat": 0.0, "lng": -0.5, "peso": 1000.0, "is_candidato": True},
        {"lat": 0.0, "lng": 0.5, "peso": 4000.0, "is_candidato": False},
    ]
    setores = [
        {"lat": 0.0, "lng": -0.05, "pessoas": 100},
    ]
    out = compute_voronoi_smoke(
        sites=sites, ring=ring, setores=setores, pool_ref=1000, pop_bairro=1000
    )
    assert out["status"] == "ok"
    assert out["pop_celula"] == 100
    assert out["pop_celula_ponderada"] == 0
    assert out["pool_voronoi"] != out["pool_voronoi_ponderado"]


def test_smoke_piramide_celula_not_scale():
    from tools.parametros_metodologia import param
    from tools.voronoi_atratividade import compute_voronoi_smoke

    ring = [(-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0), (-1.0, -1.0)]
    sites = [
        {"lat": 0.0, "lng": -0.5, "peso": 1500.0, "is_candidato": True},
        {"lat": 0.0, "lng": 0.5, "peso": 1500.0, "is_candidato": False},
    ]
    # Cell west: form bands 15-24+25-39 = 500; scale would use pessoas=800 → 800
    setores = [
        {
            "lat": 0.0,
            "lng": -0.4,
            "pessoas": 800,
            "h_15_24": 100,
            "m_15_24": 100,
            "h_25_39": 150,
            "m_25_39": 150,
            "h_40_59": 50,
            "m_40_59": 50,
            "h_60_mais": 50,
            "m_60_mais": 50,
        },
        {
            "lat": 0.0,
            "lng": 0.4,
            "pessoas": 200,
            "h_15_24": 20,
            "m_15_24": 20,
            "h_25_39": 30,
            "m_25_39": 30,
            "h_40_59": 20,
            "m_40_59": 20,
            "h_60_mais": 10,
            "m_60_mais": 10,
        },
    ]
    out = compute_voronoi_smoke(
        sites=sites,
        ring=ring,
        setores=setores,
        pool_ref=1000,
        pop_bairro=1000,
        idade_min=18,
        idade_max=39,
        perfil_ab=False,
    )
    interesse = float(param("penetracao_potencial_fitness"))
    pen = float(param("penetracao_geral"))
    expected = int(round(500 * interesse * pen))
    assert out["status"] == "ok"
    assert out["metodo_pool"] == "piramide_celula"
    assert out["estoque_primario_celula"] == 500  # 200+300 form bands
    assert out["pool_voronoi"] == expected
    assert out["pool_voronoi"] != 800  # not scale


def test_sites_from_state_carrega_censo_setor(monkeypatch):
    from tools import voronoi_atratividade as v

    rows = [
        {"lat": -3.747, "lng": -38.482, "pessoas": 800},
        {"lat": -3.748, "lng": -38.490, "pessoas": 200},
    ]
    monkeypatch.setattr(
        "tools.censo_setor_tools.carregar_setores_idade_sexo",
        lambda id_municipio, ring=None, _rows=None, **_k: [],
    )
    monkeypatch.setattr(
        "tools.censo_setor_tools.carregar_setores_censo",
        lambda id_municipio, ring=None, _rows=None, **_k: rows,
    )
    state = {
        "id_municipio": "2304400",
        "candidato_lat": -3.747,
        "candidato_lng": -38.485,
        "demografia_bairro": {"populacao": 1000},
        "concorrentes_brutos": [
            {"nome": "Rival", "lat": -3.748, "lng": -38.470, "gate_espacial": "poligono_ibge_bairro"},
        ],
        "bairro_poligono": {
            "ring": [
                (-38.50, -3.76),
                (-38.46, -3.76),
                (-38.46, -3.73),
                (-38.50, -3.73),
                (-38.50, -3.76),
            ]
        },
    }
    absorcao = {"pool_primario": 1000, "modelo_teto": "mid"}
    kw = v.sites_from_state(state, absorcao)
    assert len(kw["setores"]) == 2
    assert kw["pin_fonte"] == "explicito"
    smoke = v.compute_voronoi_smoke(**kw)
    assert smoke["status"] == "ok"
    assert smoke["pop_celula"] is not None
    assert smoke["pin_fonte"] == "explicito"


def test_ignora_a1_geoscout_usa_centroide_e_maps_gps(monkeypatch):
    import json
    from pathlib import Path

    from tools import voronoi_atratividade as v

    fixture = json.loads(
        Path("tools/fixtures/searchapi_maps_coco_fortaleza.json").read_text(encoding="utf-8")
    )
    rivals = v.concorrentes_from_searchapi_local_results(fixture)
    assert len(rivals) == 20
    assert rivals[0]["lat"] == -3.7463205

    monkeypatch.setattr(
        "tools.censo_setor_tools.carregar_setores_idade_sexo",
        lambda *a, **k: [
            {"lat": -3.745, "lng": -38.482, "pessoas": 500,
             "h_25_39": 100, "m_25_39": 100, "h_15_24": 0, "m_15_24": 0,
             "h_40_59": 50, "m_40_59": 50, "h_60_mais": 0, "m_60_mais": 0},
            {"lat": -3.740, "lng": -38.470, "pessoas": 300,
             "h_25_39": 40, "m_25_39": 40, "h_15_24": 0, "m_15_24": 0,
             "h_40_59": 20, "m_40_59": 20, "h_60_mais": 0, "m_60_mais": 0},
        ],
    )
    state = {
        "id_municipio": "2304400",
        # A1 lixo — deve ser IGNORADO
        "candidatos_geoscout": [{"lat": -3.999, "lng": -38.999, "endereco": "fake listing"}],
        "top_3_candidatos": [{"lat": -3.998, "lng": -38.998}],
        "demografia_bairro": {"populacao": 800},
        "concorrentes_brutos": rivals,
        "bairro_poligono": {
            "ring": [
                (-38.50, -3.76),
                (-38.46, -3.76),
                (-38.46, -3.73),
                (-38.50, -3.73),
                (-38.50, -3.76),
            ]
        },
        "input_params": {"idade_min": 25, "idade_max": 40},
    }
    absorcao = {"pool_primario": 1221, "modelo_teto": "mid"}
    kw = v.sites_from_state(state, absorcao)
    assert kw["pin_fonte"] == "centroide_bairro"
    cand = [s for s in kw["sites"] if s["is_candidato"]]
    assert len(cand) == 1
    # centróide do ring ≈ lat -3.745, lng -38.48 — NÃO o A1 fake
    assert abs(cand[0]["lat"] - (-3.745)) < 0.01
    assert abs(cand[0]["lng"] - (-38.48)) < 0.01
    assert abs(cand[0]["lat"] - (-3.999)) > 0.1
    rivals_sites = [s for s in kw["sites"] if not s["is_candidato"]]
    assert len(rivals_sites) >= 15
    smoke = v.compute_voronoi_smoke(**kw)
    assert smoke["status"] == "ok"
    assert smoke["pin_fonte"] == "centroide_bairro"
    assert smoke["n_sites"] >= 16
