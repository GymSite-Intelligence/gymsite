from tools.listing_candidato_normalize import normalizar_listings


def test_drop_fora_da_cidade():
    rows = [
        {
            "area_m2": 800,
            "endereco": "Centro, Diadema - SP",
            "url": "u",
            "titulo": "Galpão",
        }
    ]

    out = normalizar_listings(
        rows,
        cidade="Pirapora",
        uf="MG",
        bairro="Centro",
        lat0=-17.35,
        lng0=-44.94,
    )

    assert out == []


def test_score_distancia_zero_no_centroide():
    rows = [
        {
            "area_m2": 900,
            "endereco": "Centro, Pirapora - MG",
            "latitude": -17.35,
            "longitude": -44.94,
            "url": "u",
            "titulo": "Galpão",
        }
    ]

    out = normalizar_listings(
        rows,
        cidade="Pirapora",
        uf="MG",
        bairro="Centro",
        lat0=-17.35,
        lng0=-44.94,
    )

    assert len(out) == 1
    assert out[0]["score_geoscout"] == 10.0
    assert out[0]["qualidade_sinal"] == "direto-listing-bairro"
    assert out[0]["score_geoscout"] != 8.5


def test_sem_area_drop():
    rows = [
        {
            "area_m2": None,
            "endereco": "Centro, Pirapora - MG",
            "url": "u",
            "titulo": "Galpão",
        }
    ]

    assert normalizar_listings(
        rows,
        cidade="Pirapora",
        uf="MG",
        bairro="Centro",
        lat0=-17.35,
        lng0=-44.94,
    ) == []


def test_sem_endereco_e_sem_coordenada_drop():
    rows = [{"area_m2": 700, "url": "u", "titulo": "Galpão"}]

    assert normalizar_listings(
        rows,
        cidade="Pirapora",
        uf="MG",
        bairro="Centro",
        lat0=-17.35,
        lng0=-44.94,
    ) == []


def test_sem_coordenada_fica_com_score_zero():
    rows = [
        {
            "area_m2": 700,
            "endereco": "Centro, Pirapora - MG",
            "url": "u",
            "titulo": "Loja",
        }
    ]

    out = normalizar_listings(
        rows,
        cidade="Pirapora",
        uf="MG",
        bairro="Centro",
        lat0=-17.35,
        lng0=-44.94,
    )

    assert out[0]["score_geoscout"] == 0.0
    assert out[0]["geocoded"] is False
