"""PONTO 52/55/56/80 — regra de gênero + faixa-alvo."""

from agents.a9_positioning_strategist import _publico_dominante
from tools.genero_estrategia import (
    aplicar_regra_genero,
    classificar_genero,
    extrair_genero_do_state,
    sugestoes_genero_errc,
)


def test_t1_feminino_no_limiar():
    r = classificar_genero(54.0, 46.0, limiar=8)
    assert r["diff_pp"] == 8.0
    assert r["genero"] == "feminino"


def test_t2_misto_abaixo_limiar():
    r = classificar_genero(52.0, 48.0, limiar=8)
    assert r["diff_pp"] == 4.0
    assert r["genero"] == "misto"


def test_t3_masculino():
    r = classificar_genero(40.0, 60.0, limiar=8)
    assert r["genero"] == "masculino"


def test_t4_extrair_coco_faixa_alvo():
    state = {
        "input_params": {"publico_alvo": "25-40", "genero_alvo": "misto"},
        "demografia_bairro": {
            "perfil_idade_sexo_bairro": {
                "faixa_idade": "25-39",
                "pct_mulheres": 54.0,
                "pct_homens": 46.0,
                "total": 5299,
                "segmentos": {
                    "25-39": {
                        "total": 5299,
                        "pct_mulheres": 54.0,
                        "pct_homens": 46.0,
                    },
                    "40-59": {
                        "total": 6606,
                        "pct_mulheres": 55.6,
                        "pct_homens": 44.4,
                    },
                },
            }
        },
    }
    r = extrair_genero_do_state(state, limiar=8)
    assert r["genero"] == "feminino"
    assert r["nivel_base"] == "bairro_faixa_alvo"
    assert r["faixa_idade"] == "25-39"


def test_t5_sem_dados():
    r = extrair_genero_do_state({}, limiar=8)
    assert r["genero"] == "misto"
    assert r["nivel_base"] == "nenhum"


def test_t6_dados_invalidos():
    r = classificar_genero("abc", None, limiar=8)
    assert r["genero"] == "misto"
    assert r["nivel_base"] == "indeterminado"


def test_aplicar_sobrescreve_misto():
    state = {
        "input_params": {"publico_alvo": "25-40"},
        "demografia_bairro": {
            "perfil_idade_sexo_bairro": {
                "faixa_idade": "25-39",
                "total": 100,
                "segmentos": {
                    "25-39": {"total": 100, "pct_mulheres": 54.0, "pct_homens": 46.0},
                },
            }
        },
    }
    r = aplicar_regra_genero("misto", state, limiar=8)
    assert r["genero_final"] == "feminino"
    assert r["sobrescrito"] is True
    assert "Estratégia ajustada" in (r["insight"] or "")


def test_ponto80_a9_usa_faixa_alvo_nao_max_headcount():
    state = {
        "input_params": {"publico_alvo": "25-40"},
        "demografia_bairro": {
            "perfil_idade_sexo_bairro": {
                "faixa_idade": "25-39",
                "segmentos": {
                    "25-39": {"total": 5299, "pct_mulheres": 54.0, "pct_homens": 46.0},
                    "40-59": {"total": 6606, "pct_mulheres": 55.6, "pct_homens": 44.4},
                },
            }
        },
    }
    pub = _publico_dominante(state)
    assert pub is not None
    assert pub[0] == "25-39"
    assert pub[1] == 54


def test_sugestoes_genero_feminino():
    sugs = sugestoes_genero_errc("feminino", 54.0)
    assert len(sugs) == 1
    assert "yoga" in sugs[0].lower() or "pilates" in sugs[0].lower()
