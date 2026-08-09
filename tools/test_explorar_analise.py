def test_parse_publico_alvo_idades():
    from tools.explorar_analise import parse_publico_alvo_idades

    assert parse_publico_alvo_idades("25-39") == (25, 39)
    assert parse_publico_alvo_idades("60+") == (60, 120)
    assert parse_publico_alvo_idades("") == (None, None)


def test_publico_alvo_define_faixa_primaria():
    from tools.explorar_analise import run_explorar_analise

    out = run_explorar_analise(
        lat=-3.745,
        lng=-38.485,
        lente="1km",
        cidade="Fortaleza",
        bairro="Cocó",
        uf="CE",
        publico_alvo="60+",
        area_candidato_m2=400,
        _concorrentes=[],
        _setores=[
            {
                "lat": -3.745,
                "lng": -38.485,
                "pessoas": 1000,
                "h_25_39": 200,
                "m_25_39": 200,
                "h_40_59": 100,
                "m_40_59": 100,
                "h_15_24": 50,
                "m_15_24": 50,
                "h_60_mais": 80,
                "m_60_mais": 70,
            }
        ],
    )
    absb = out["absorcao_margem_fresca"]
    assert absb["faixas_primario"] == ["60+"]
    assert "15-24" in absb["faixas_secundario"]
    assert "formulário" not in str(absb.get("nota_modelo_secundario") or "").lower()


def test_lente_1km_same_base_for_rivals_and_absorcao():
    from tools.explorar_analise import run_explorar_analise

    rivals = [
        {"nome": "Academia A", "lat": -3.746, "lng": -38.489, "tipos": ["gym"], "rating": 4.5, "reviews": 10},
        {"nome": "Academia B", "lat": -3.747, "lng": -38.480, "tipos": ["gym"], "rating": 4.0, "reviews": 5},
    ]
    out = run_explorar_analise(
        lat=-3.745,
        lng=-38.485,
        lente="1km",
        cidade="Fortaleza",
        bairro="Cocó",
        uf="CE",
        _concorrentes=rivals,
        _setores=[
            {
                "lat": -3.745,
                "lng": -38.485,
                "pessoas": 1000,
                "h_25_39": 200,
                "m_25_39": 200,
                "h_40_59": 100,
                "m_40_59": 100,
                "h_15_24": 50,
                "m_15_24": 50,
                "h_60_mais": 30,
                "m_60_mais": 30,
            }
        ],
    )
    assert out["lente"] == "1km"
    assert "score" not in out and "nota_0_10" not in out
    assert out["absorcao_margem_fresca"]["rotulo"] in ("fresco", "misto", "roubo")
    assert len(out["concorrentes"]) >= 1
    assert "1 km" in out["base_espacial_label"].lower() or "1km" in out["base_espacial_label"].lower()


def test_places_location_latitude_counts_as_rival():
    from tools.explorar_analise import run_explorar_analise

    out = run_explorar_analise(
        lat=-3.745,
        lng=-38.485,
        lente="1km",
        _concorrentes=[
            {
                "displayName": {"text": "Parque Esportes"},
                "location": {"latitude": -3.74632, "longitude": -38.4891},
                "rating": 4.5,
                "userRatingCount": 10,
            }
        ],
        _setores=[],
    )
    assert len(out["concorrentes"]) == 1
    assert out["concorrentes"][0]["nome"] == "Parque Esportes"


def test_no_ondeabrir_score_keys():
    from tools.explorar_analise import run_explorar_analise

    out = run_explorar_analise(
        lat=-3.74,
        lng=-38.48,
        lente="500m",
        _concorrentes=[],
        _setores=[],
    )
    blob = str(out).lower()
    assert "oportunidade clara" not in blob


def test_explorar_descarta_luta_clinica_mesmo_com_poucas_academias():
    from tools.explorar_analise import run_explorar_analise

    out = run_explorar_analise(
        lat=-7.067,
        lng=-34.844,
        lente="1km",
        tipo_negocio="academia",
        cidade="João Pessoa",
        bairro="Bessa",
        uf="PB",
        _concorrentes=[
            {
                "nome": "Checkmat Bessa",
                "lat": -7.068,
                "lng": -34.845,
                "tipos": ["gym"],
                "rating": 5,
            },
            {
                "nome": "Academia de Cordel do Vale",
                "lat": -7.0675,
                "lng": -34.8445,
                "tipos": ["gym"],
                "rating": 3.7,
            },
            {
                "nome": "DoctorFit João Pessoa – Bessa",
                "lat": -7.069,
                "lng": -34.846,
                "tipos": ["gym"],
                "rating": 4.9,
            },
            {
                "nome": "Espaço Físico Academia",
                "lat": -7.0682,
                "lng": -34.8452,
                "tipos": ["gym"],
                "rating": 4.5,
            },
        ],
        _setores=[],
    )
    nomes = {c["nome"] for c in out["concorrentes"]}
    assert "Espaço Físico Academia" in nomes
    assert "Checkmat Bessa" not in nomes
    assert "Academia de Cordel do Vale" not in nomes
    assert "DoctorFit João Pessoa – Bessa" not in nomes


def test_tipo_pilates_aplica_gate():
    from tools.explorar_analise import run_explorar_analise

    rivals = [
        {
            "nome": "Smart Fit Cocó",
            "lat": -3.746,
            "lng": -38.489,
            "tipos": ["gym"],
            "rating": 4.5,
            "reviews": 10,
        },
        {
            "nome": "Studio Pilates Cocó",
            "lat": -3.7461,
            "lng": -38.4891,
            "tipos": ["pilates"],
            "rating": 4.8,
            "reviews": 20,
        },
        {
            "nome": "Pilates Aldeota",
            "lat": -3.7455,
            "lng": -38.486,
            "tipos": ["pilates"],
            "rating": 4.6,
            "reviews": 12,
        },
    ]
    out = run_explorar_analise(
        lat=-3.745,
        lng=-38.485,
        lente="1km",
        tipo_negocio="studio_pilates",
        _concorrentes=rivals,
        _setores=[],
    )
    nomes = {c["nome"] for c in out["concorrentes"]}
    assert out["tipo_negocio"] == "studio_pilates"
    assert "Studio Pilates Cocó" in nomes
    assert "Pilates Aldeota" in nomes
    assert "Smart Fit Cocó" not in nomes


def test_fetch_query_usa_tipo_pilates(monkeypatch):
    captured: dict = {}

    def fake_search(query, max_results=40, region="", **_k):
        captured["query"] = query
        captured["region"] = region
        captured["ll"] = (_k.get("lat"), _k.get("lng"))
        return []

    monkeypatch.setattr(
        "tools.competitor_tools._searchapi_maps_textsearch", fake_search
    )
    from tools.explorar_analise import run_explorar_analise

    run_explorar_analise(
        lat=-3.745,
        lng=-38.485,
        lente="1km",
        cidade="Fortaleza",
        bairro="Cocó",
        uf="CE",
        tipo_negocio="studio_pilates",
        _setores=[],
    )
    assert "pilates" in captured["query"].lower()
    assert captured["ll"] == (-3.745, -38.485)


def test_endereco_infere_coco_na_query_maps(monkeypatch):
    captured: dict = {}

    def fake_search(query, max_results=40, region="", **_k):
        captured["query"] = query
        captured["region"] = region
        return []

    monkeypatch.setattr(
        "tools.competitor_tools._searchapi_maps_textsearch", fake_search
    )
    from tools.explorar_analise import run_explorar_analise

    run_explorar_analise(
        lat=-3.749,
        lng=-38.480,
        lente="1km",
        endereco="Cocó, Fortaleza, Ceará, Brasil",
        tipo_negocio="academia",
        _setores=[],
    )
    q = captured["query"].lower()
    assert "academia" in q
    assert "coco" in q or "fortaleza" in q
