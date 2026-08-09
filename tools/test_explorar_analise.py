def test_base_label_sem_centroide():
    from tools.explorar_analise import _base_label

    um = _base_label(lente="1km", bairro="Cocó", ring=None)
    assert "centróide" not in um.lower()
    assert "centroide" not in um.lower()
    assert "Raio 1 km a partir do centro do bairro" in um
    assert "IBGE Censo 2022" in um
    bairro = _base_label(lente="bairro", bairro="Cocó", ring=[(0, 0), (1, 0), (0, 1)])
    assert "centróide" not in bairro.lower()
    assert "Recorte do bairro Cocó" in bairro


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


def test_explorar_descarta_academia_ao_ar_livre():
    from tools.explorar_analise import run_explorar_analise

    out = run_explorar_analise(
        lat=-3.745,
        lng=-38.485,
        lente="1km",
        tipo_negocio="academia",
        _concorrentes=[
            {
                "nome": "Academia ao ar livre Unimed",
                "lat": -3.746,
                "lng": -38.486,
                "tipos": ["gym"],
                "rating": 5,
            },
            {
                "nome": "Academia Athletic Fortal",
                "lat": -3.7462,
                "lng": -38.4862,
                "tipos": ["gym"],
                "rating": 4.3,
            },
        ],
        _setores=[],
    )
    nomes = {c["nome"] for c in out["concorrentes"]}
    assert "Academia Athletic Fortal" in nomes
    assert "Academia ao ar livre Unimed" not in nomes
    assert "centróide" not in out["base_espacial_label"].lower()
    blob = " ".join(
        str(v) for v in (out["absorcao_margem_fresca"].get("leituras") or {}).values()
    ).lower()
    assert "cap_parque" not in blob
    assert "matr_m2" not in blob


def test_explorar_reclamacoes_so_nota_baixa(monkeypatch):
    from tools import explorar_analise as ea

    def fake_fetch(*, place_id, data_id=None):
        return [
            {"text": "Lotada no pico", "rating": 2, "user": {"name": "Ana"}},
            {"text": "Excelente", "rating": 5, "user": {"name": "Bia"}},
            {"text": "Ar-condicionado ruim", "rating": 3, "user": {"name": "Caio"}},
        ]

    monkeypatch.setattr("tools.explorar_reviews.fetch_explorar_reviews", fake_fetch)
    out = ea.run_explorar_analise(
        lat=-3.745,
        lng=-38.485,
        lente="1km",
        _concorrentes=[
            {
                "nome": "Academia Athletic Fortal",
                "lat": -3.746,
                "lng": -38.486,
                "tipos": ["gym"],
                "id": "ChIJ_test",
                "formattedAddress": "Av. Santos Dumont, 1000",
                "rating": 4.3,
            }
        ],
        _setores=[],
    )
    riv = out["concorrentes"][0]
    assert riv["endereco"] == "Av. Santos Dumont, 1000"
    recs = riv["reclamacoes"]
    assert len(recs) == 2
    assert all(r["rating"] <= 3 for r in recs)
    assert "Lotada" in recs[0]["texto"]


def test_explorar_reclamacoes_error_searchapi_vira_vazio(monkeypatch):
    from tools import explorar_analise as ea

    monkeypatch.setattr(
        "tools.explorar_reviews.fetch_explorar_reviews",
        lambda **k: [],
    )
    out = ea.run_explorar_analise(
        lat=-3.745,
        lng=-38.485,
        lente="1km",
        _concorrentes=[
            {
                "nome": "Academia Uniq Club Cocó",
                "lat": -3.746,
                "lng": -38.486,
                "tipos": ["gym"],
                "id": "ChIJCb3yfcJHxwcR0CZUhe1hc9E",
                "rating": 4.5,
            }
        ],
        _setores=[],
    )
    assert out["concorrentes"][0]["reclamacoes"] == []


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
