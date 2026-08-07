from tools.matriz_demo_saturacao import attach_matriz_demo_saturacao


def test_attach_armadilha_sets_override():
    state = {
        "demografia_bairro": {
            "populacao": 50000,
            "censo_base": "poligono_ibge_bairro",
            "renda_media_per_capita": 5000,
        },
        "concorrentes_brutos": [
            {"nome": "Bodytech", "gate_espacial": "poligono_ibge_bairro"},
            {"nome": "Bio Ritmo", "gate_espacial": "poligono_ibge_bairro"},
            {"nome": "Smart Fit", "gate_espacial": "poligono_ibge_bairro"},
        ],
    }
    parsed = {
        "veredito_posicionamento": "OCEANO_AZUL",
        "headroom_renda": {"renda_percentil": 0.9, "renda_pc": 5000},
    }
    r = attach_matriz_demo_saturacao(state, parsed)
    assert r is not None
    assert parsed["matriz_demo_saturacao"]["quadrante"] == "Armadilha de Renda"
    assert parsed["matriz_override"] is True
    assert parsed["matriz_demo_saturacao"]["fonte_espacial"] == "poligono_ibge_bairro"


def test_attach_prefers_pip_gate():
    state = {
        "demografia_bairro": {"populacao": 40000, "censo_base": "poligono_ibge_bairro"},
        "concorrentes_brutos": [
            {"nome": "Bodytech", "gate_espacial": "poligono_ibge_bairro"},
            {"nome": "Bio Ritmo", "gate_espacial": "poligono_ibge_bairro"},
            {"nome": "Longe", "gate_espacial": "raio_3km"},
        ],
    }
    parsed = {
        "veredito_posicionamento": "OCEANO_AZUL",
        "headroom_renda": {"renda_percentil": 0.9},
    }
    attach_matriz_demo_saturacao(state, parsed)
    m = parsed["matriz_demo_saturacao"]
    assert m["n_poligono"] == 2
    assert m["fonte_espacial"] == "poligono_ibge_bairro"
