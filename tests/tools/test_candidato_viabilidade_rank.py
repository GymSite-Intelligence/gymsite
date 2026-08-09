from tools.candidato_viabilidade_rank import (
    rank_candidatos_viabilidade,
    score_payback_norm,
)


def _financeiro_mid() -> dict:
    return {
        "cenarios": {
            "mid": {
                "investimento_total": 240_000,
                "lucro_mensal_estimado": 20_000,
                "custos_detalhados": {
                    "aluguel": 20_000,
                    "condominio": 2_000,
                },
            }
        }
    }


def test_payback_norm_limites():
    assert score_payback_norm(12) == 1.0
    assert score_payback_norm(48) == 0.0
    assert score_payback_norm(999) == 0.0
    assert score_payback_norm(30) == 0.5


def test_nunca_usa_price_raw():
    candidate = {
        "nome": "Galpão",
        "endereco": "Centro, Pirapora - MG",
        "score_geoscout": 8,
        "area_m2": 800,
        "aluguel_estimado": 10_000,
        "aluguel_unitario_m2": 12.5,
        "aluguel_fonte": "MRLR",
        "price_raw": "R$ 999.999",
    }

    ranked = rank_candidatos_viabilidade([candidate], _financeiro_mid())

    assert ranked[0]["aluguel_mrlr_mensal"] == 10_000
    assert ranked[0]["payback_est_meses"] == 7.7
    assert "999" not in ranked[0]["carimbo_aluguel"]


def test_payback_melhor_supera_geo_um_pouco_maior():
    candidates = [
        {
            "nome": "Geo melhor",
            "endereco": "A",
            "score_geoscout": 9,
            "area_m2": 800,
            "aluguel_estimado": 30_000,
            "aluguel_unitario_m2": 37.5,
            "aluguel_fonte": "MRLR",
        },
        {
            "nome": "Payback melhor",
            "endereco": "B",
            "score_geoscout": 7,
            "area_m2": 800,
            "aluguel_estimado": 10_000,
            "aluguel_unitario_m2": 12.5,
            "aluguel_fonte": "MRLR",
        },
    ]

    ranked = rank_candidatos_viabilidade(candidates, _financeiro_mid())

    assert ranked[0]["nome"] == "Payback melhor"
    assert ranked[0]["score_composto"] > ranked[1]["score_composto"]


def test_sem_financeiro_preserva_geo_com_aviso():
    candidates = [
        {"nome": "B", "endereco": "B", "score_geoscout": 5},
        {"nome": "A", "endereco": "A", "score_geoscout": 8},
    ]

    ranked = rank_candidatos_viabilidade(candidates, {})

    assert [item["nome"] for item in ranked] == ["A", "B"]
    assert ranked[0]["payback_est_meses"] is None
    assert ranked[0]["aviso_viabilidade"]
