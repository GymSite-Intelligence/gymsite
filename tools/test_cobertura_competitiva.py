"""B1+B2 — cobertura competitiva + supressão de gaps universais."""
from __future__ import annotations

from tools.cobertura_competitiva import (
    filtrar_gaps_universais,
    mapa_servicos_da_cobertura,
    montar_cobertura_competitiva,
)
from tools.parametros_metodologia import param, param_list


def _coco_fixture():
    no_bairro = [
        {"place_id": "pid_max", "nome": "Academias Max Forma", "deep": True},
        {"place_id": "pid_uniq", "nome": "Academia Uniq Club Cocó", "deep": False},
        {"place_id": "pid_green", "nome": "CT Greenlife", "deep": False},
        {"place_id": "pid_mundo", "nome": "Mundo Fitness Fortaleza", "deep": False},
        {"place_id": "pid_ath", "nome": "Academia Athletic Fortal", "deep": True},
        {"place_id": "pid_keep", "nome": "Keep in shape Academia", "deep": False},
        {"place_id": "pid_kcp", "nome": "ACADEMIA KCP", "deep": False},
    ]
    competitors_set = [
        {
            "place_id": "pid_max",
            "nome": "Academias Max Forma",
            "servicos_oferecidos": [
                "avaliacao", "danca", "estetica", "funcional", "musculacao",
                "personal", "pilates", "recovery",
            ],
            "oferta_mapeada": {
                "modalidades": [
                    "avaliacao", "danca", "estetica", "funcional", "musculacao",
                    "personal", "pilates", "recovery",
                ],
                "fontes": ["site", "instagram"],
            },
        },
        {
            "place_id": "pid_ath",
            "nome": "Academia Athletic Fortal",
            "servicos_oferecidos": [
                "area_kids", "danca", "estetica", "funcional", "lutas",
                "musculacao", "personal",
            ],
            "oferta_mapeada": {
                "modalidades": [
                    "area_kids", "danca", "estetica", "funcional", "lutas",
                    "musculacao", "personal",
                ],
                "fontes": ["site", "instagram"],
            },
        },
    ]
    oferta = {
        "oferta_concorrentes": {
            "pid_max": {
                "nome": "Academias Max Forma",
                "modalidades": [
                    "avaliacao", "danca", "estetica", "funcional", "musculacao",
                    "personal", "pilates", "recovery",
                ],
            },
            "pid_ath": {
                "nome": "Academia Athletic Fortal",
                "modalidades": [
                    "area_kids", "danca", "estetica", "funcional", "lutas",
                    "musculacao", "personal",
                ],
            },
        }
    }
    return no_bairro, competitors_set, oferta


def test_b1_todo_gated_no_denominador():
    nb, cs, oferta = _coco_fixture()
    cov = montar_cobertura_competitiva(
        no_bairro=nb, competitors_set=cs, oferta_concorrentes=oferta,
    )
    assert cov is not None
    assert cov["gated_n"] == 7
    assert len(cov["oferta_por_gated"]) == 7
    assert cov["n_com_oferta"] == 2
    assert cov["cobertura_amostral"] == round(2 / 7, 4)

    deep = [v for v in cov["oferta_por_gated"].values() if v["profundidade"] == "analisado"]
    mapped = [v for v in cov["oferta_por_gated"].values() if v["profundidade"] == "mapeado"]
    assert len(deep) == 2
    assert len(mapped) == 5
    assert all(v["servicos"] for v in deep)
    assert all(v["servicos"] == [] for v in mapped)


def test_b1_mapa_de_igual_n_com_oferta():
    nb, cs, oferta = _coco_fixture()
    cov = montar_cobertura_competitiva(
        no_bairro=nb, competitors_set=cs, oferta_concorrentes=oferta,
    )
    mapa, _ = mapa_servicos_da_cobertura(cov)
    assert mapa["Musculação"]["de"] == 2
    assert mapa["Musculação"]["oferecem"] == 2
    assert mapa["Spinning"]["oferecem"] == 0
    assert mapa["Spinning"]["de"] == 2
    assert mapa["Crossfit"]["oferecem"] == 0
    assert mapa["Aulas/espaço kids"]["oferecem"] == 1


def test_b2_spinning_artefato_quando_cobertura_baixa():
    nb, cs, oferta = _coco_fixture()
    cov = montar_cobertura_competitiva(
        no_bairro=nb, competitors_set=cs, oferta_concorrentes=oferta,
    )
    assert cov["cobertura_amostral"] < param("limiar_cobertura_gap")

    gaps = ["Spinning", "Crossfit", "Natação/Hidro", "Nutrição integrada", "Aulas/espaço kids"]
    # kids já oferecido → não entra como gap na prática; aqui testamos classificação.
    validados = filtrar_gaps_universais(
        ["Spinning", "Crossfit", "Natação/Hidro", "Nutrição integrada"],
        cobertura=cov,
    )
    by = {g["servico"]: g for g in validados}
    assert by["Spinning"]["tipo"] == "artefato_cobertura"
    assert by["Spinning"]["incluir_no_errc"] is False
    assert by["Crossfit"]["tipo"] == "real"
    assert by["Crossfit"]["incluir_no_errc"] is True
    assert by["Natação/Hidro"]["incluir_no_errc"] is True
    assert by["Nutrição integrada"]["incluir_no_errc"] is True


def test_b2_universal_real_quando_cobertura_alta():
    cov = {
        "gated_n": 5,
        "n_com_oferta": 4,
        "cobertura_amostral": 0.8,
        "oferta_por_gated": {},
    }
    validados = filtrar_gaps_universais(["Spinning"], cobertura=cov)
    assert validados[0]["tipo"] == "real"
    assert validados[0]["confianca"] == "alta"
    assert validados[0]["incluir_no_errc"] is True


def test_b1_fail_soft_sem_gated():
    cov = montar_cobertura_competitiva(no_bairro=[], competitors_set=[], oferta_concorrentes=None)
    assert cov is not None
    assert cov["gated_n"] == 0
    assert cov["oferta_por_gated"] == {}


def test_params_list_universais():
    univ = param_list("servicos_universais")
    assert "Spinning" in univ
    assert "Musculação" in univ
    nich = param_list("servicos_nicho_gap")
    assert "Crossfit" in nich
