from tools.parametros_metodologia import param


def test_area_proxy_seeds():
    assert param("area_proxy_low_m2") == 1000.0
    assert param("area_proxy_mid_m2") == 1500.0
    assert param("area_proxy_premium_m2") == 2000.0
    assert param("area_proxy_nicho_desconhecido_m2") == 1250.0


def test_form_25_40_maps_core_and_maduro():
    from tools.absorcao_margem_fresca import (
        faixas_primario_from_idade,
        faixas_secundario_from_primario,
    )

    p = faixas_primario_from_idade(25, 40)
    assert p == ["25-39", "40-59"]
    assert faixas_secundario_from_primario(p) == ["15-24", "60+"]


def test_form_25_39_core_only():
    from tools.absorcao_margem_fresca import (
        faixas_primario_from_idade,
        faixas_secundario_from_primario,
    )

    p = faixas_primario_from_idade(25, 39)
    assert p == ["25-39"]
    assert "40-59" in faixas_secundario_from_primario(p)


def test_pool_duas_camadas_tres_bases():
    from tools.absorcao_margem_fresca import absorcao_margem_fresca

    segs = {
        "15-24": {"total": 7850},
        "25-39": {"total": 18420},
        "40-59": {"total": 12100},
        "60+": {"total": 8200},
    }
    out = absorcao_margem_fresca(
        concorrentes=[],
        pop_poligono=60165,
        area_candidato_m2=1500.0,
        modelo_cenario="mid",
        perfil_ab=True,
        segmentos=segs,
        idade_min=25,
        idade_max=40,
        fonte_espacial="poligono_ibge",
    )
    interesse = param("penetracao_potencial_fitness")
    pen = param("penetracao_bairro_ab")
    assert out["faixas_primario"] == ["25-39", "40-59"]
    assert out["estoque_primario"] == 30520
    assert out["estoque_secundario"] == 16050
    assert out["pool_primario"] == int(round(30520 * interesse * pen))
    assert out["pool_secundario"] == int(round(16050 * interesse * pen))
    assert out["pool_total_15mais"] == int(round(46570 * interesse * pen))
    assert out["pool_demografico"] == out["pool_primario"]
    assert out["interesse_fitness"] == interesse
    # pool_primario ~1221 < teto 2100, margem > 0 → misto (cap=0)
    assert out["rotulo"] == "misto"
    assert out["margem_fresca"] == out["pool_primario"]
    assert 0 < out["margem_fresca"] < out["teto_unidade"]


def test_fallback_sem_piramide():
    from tools.absorcao_margem_fresca import absorcao_margem_fresca

    out = absorcao_margem_fresca(
        concorrentes=[],
        pop_poligono=100_000,
        area_candidato_m2=1500.0,
        modelo_cenario="mid",
        perfil_ab=False,
        segmentos=None,
    )
    interesse = param("penetracao_potencial_fitness")
    pen = param("penetracao_geral")
    assert out["pool_primario"] == int(round(100_000 * interesse * pen))
    assert "fallback_pop_total" in out["carimbos"]["pool_demografico"]


def test_golden_spec_example_mid():
    """4 Low + 2 Mid + 1 Premium; unidade Mid 1500 m² — fallback pool."""
    from tools.absorcao_margem_fresca import absorcao_margem_fresca

    cs = (
        [
            {"nome": "Smart Fit A"},
            {"nome": "Smart Fit B"},
            {"nome": "Smart Fit C"},
            {"nome": "Smart Fit D"},
        ]
        + [{"nome": "Local Mid", "ticket_medio": 180}] * 2
        + [{"nome": "Bodytech X"}]
    )
    out = absorcao_margem_fresca(
        concorrentes=cs,
        pop_poligono=100_000,
        area_candidato_m2=1500.0,
        modelo_cenario="mid",
        perfil_ab=False,
        fonte_espacial="poligono_ibge",
    )
    interesse = param("penetracao_potencial_fitness")
    pen = param("penetracao_geral")
    pool = int(round(100_000 * interesse * pen))
    assert out["teto_unidade"] == 2100
    assert out["capacidade_parque_estimada"] == 14200
    assert out["pool_demografico"] == pool
    assert out["margem_fresca"] == pool - 14200
    assert out["rotulo"] == "roubo"
    assert out["area_proxy_usada"]["low"] == 1000
    assert out["base_espacial"] in ("poligono_ibge", "raio_fallback")
    assert "voronoi" not in str(out["base_espacial"])


def test_rotulo_fresco():
    from tools.absorcao_margem_fresca import absorcao_margem_fresca

    # pool fallback 100k×0.4×0.045=1800; teto 1000×1.4=1400 → fresco
    out = absorcao_margem_fresca(
        concorrentes=[],
        pop_poligono=100_000,
        area_candidato_m2=1000.0,
        modelo_cenario="mid",
        perfil_ab=False,
        fonte_espacial="raio_fallback",
    )
    assert out["capacidade_parque_estimada"] == 0
    assert out["rotulo"] == "fresco"
    assert out["margem_fresca"] >= out["teto_unidade"]


def test_rotulo_misto():
    from tools.absorcao_margem_fresca import absorcao_margem_fresca

    # cap 1 Low = 2200; pool ≈ 3000 → margem 800 < teto 2100 → misto
    # pool = pop × 0.4 × 0.045 → pop = 3000 / 0.018
    out = absorcao_margem_fresca(
        concorrentes=[{"nome": "Smart Fit"}],
        pop_poligono=int(3000 / 0.018),
        area_candidato_m2=1500.0,
        modelo_cenario="mid",
        perfil_ab=False,
    )
    assert out["rotulo"] == "misto"


def test_nicho_desconhecido_uses_1250_x_mid():
    from tools.absorcao_margem_fresca import absorcao_margem_fresca
    from tools.matriz_demo_saturacao import classificar_tier_concorrente

    c = {"nome": "Studio X"}
    assert classificar_tier_concorrente(c) == "desconhecido"
    out = absorcao_margem_fresca(
        concorrentes=[c],
        pop_poligono=50_000,
        area_candidato_m2=800.0,
        modelo_cenario="mid",
        perfil_ab=False,
    )
    expected = int(round(1250 * param("matr_m2_mid_realista")))
    assert out["capacidade_parque_estimada"] == expected


def test_attach_writes_parsed():
    from tools.absorcao_margem_fresca import attach_absorcao_margem_fresca

    state = {
        "demografia_bairro": {
            "populacao": 60165,
            "renda_media_per_capita": 4812,
            "censo_base": "poligono_ibge_bairro",
            "perfil_idade_sexo_bairro": {
                "segmentos": {
                    "15-24": {"total": 7850},
                    "25-39": {"total": 18420},
                    "40-59": {"total": 12100},
                    "60+": {"total": 8200},
                },
            },
        },
        "input_params": {"idade_min": 25, "idade_max": 40},
        "concorrentes_brutos": [
            {"nome": "Smart Fit", "gate_espacial": "poligono_ibge_bairro"},
            {"nome": "Bodytech", "gate_espacial": "poligono_ibge_bairro"},
        ],
        "area_m2": 1500,
        "modelo_recomendado": "mid",
    }
    parsed: dict = {}
    out = attach_absorcao_margem_fresca(state, parsed)
    assert out is not None
    abs_ = parsed["absorcao_margem_fresca"]
    assert abs_["rotulo"] in ("fresco", "misto", "roubo")
    assert abs_["base_espacial"] == "poligono_ibge"
    assert abs_["estoque_primario"] == 30520
    assert abs_["pool_primario"] == abs_["pool_demografico"]
    assert abs_["faixas_primario"] == ["25-39", "40-59"]


def test_roubo_derruba_oceano_azul():
    from tools.absorcao_margem_fresca import aplicar_veto_oceano_por_roubo

    parsed = {
        "veredito_posicionamento": "OCEANO_AZUL",
        "fonte_veredito": "deterministico_headroom_renda",
        "absorcao_margem_fresca": {"rotulo": "roubo"},
    }
    assert aplicar_veto_oceano_por_roubo(parsed) is True
    assert parsed["veredito_posicionamento"] == "TRANSICAO"
    assert parsed["veredito_antes_veto_absorcao"] == "OCEANO_AZUL"
    assert parsed["veto_absorcao_roubo"] is True
    assert "roubo" in str(parsed["fonte_veredito"]).lower()


def test_fresco_nao_derruba_oceano():
    from tools.absorcao_margem_fresca import aplicar_veto_oceano_por_roubo

    parsed = {
        "veredito_posicionamento": "OCEANO_AZUL",
        "absorcao_margem_fresca": {"rotulo": "fresco"},
    }
    assert aplicar_veto_oceano_por_roubo(parsed) is False
    assert parsed["veredito_posicionamento"] == "OCEANO_AZUL"
    assert "veto_absorcao_roubo" not in parsed


def test_roubo_nao_piora_vermelho_nem_transicao():
    from tools.absorcao_margem_fresca import aplicar_veto_oceano_por_roubo

    for v in ("VERMELHO", "TRANSICAO", "INDETERMINADO"):
        parsed = {
            "veredito_posicionamento": v,
            "absorcao_margem_fresca": {"rotulo": "roubo"},
        }
        assert aplicar_veto_oceano_por_roubo(parsed) is False
        assert parsed["veredito_posicionamento"] == v


def test_attach_adds_voronoi_smoke_without_changing_rotulo(monkeypatch):
    from tools import absorcao_margem_fresca as m

    def fake_smoke(**kwargs):
        return {
            "status": "ok",
            "motivo": None,
            "pop_bairro": 1000,
            "pop_celula": 400,
            "pop_celula_ponderada": 350,
            "pool_ref": kwargs["pool_ref"],
            "pool_voronoi": int(round(kwargs["pool_ref"] * 0.4)),
            "pool_voronoi_ponderado": int(round(kwargs["pool_ref"] * 0.35)),
            "delta_pct": -0.6,
            "n_sites": 2,
            "n_setores_celula": 1,
            "peso_candidato": 1500.0,
            "carimbo": "ok · smoke · IBGE · n/a",
        }

    monkeypatch.setattr(
        "tools.voronoi_atratividade.compute_voronoi_smoke",
        fake_smoke,
    )

    state = {
        "demografia_bairro": {
            "populacao": 60165,
            "renda_media_per_capita": 4812,
            "perfil_idade_sexo_bairro": {
                "segmentos": {
                    "15-24": {"total": 7850},
                    "25-39": {"total": 18420},
                    "40-59": {"total": 12100},
                    "60+": {"total": 8200},
                },
            },
        },
        "input_params": {"idade_min": 25, "idade_max": 40},
        "concorrentes_brutos": [
            {
                "nome": "A",
                "lat": -3.75,
                "lng": -38.48,
                "gate_espacial": "poligono_ibge_bairro",
            },
            {
                "nome": "B",
                "lat": -3.76,
                "lng": -38.47,
                "gate_espacial": "poligono_ibge_bairro",
            },
        ],
        "area_m2": 1500,
        "candidato_lat": -3.755,
        "candidato_lng": -38.475,
        "bairro_poligono": {
            "ring": [
                (-38.50, -3.78),
                (-38.45, -3.78),
                (-38.45, -3.73),
                (-38.50, -3.73),
                (-38.50, -3.78),
            ]
        },
        "modelo_recomendado": "mid",
    }
    parsed: dict = {"veredito_posicionamento": "TRANSICAO"}
    out = m.attach_absorcao_margem_fresca(state, parsed)
    assert out is not None
    abs_ = parsed["absorcao_margem_fresca"]
    assert abs_["rotulo"] in ("fresco", "misto", "roubo")
    assert "voronoi_smoke" in abs_
    assert abs_["voronoi_smoke"]["status"] == "ok"
    assert abs_["base_espacial"] in ("poligono_ibge", "raio_fallback")
    assert abs_["base_espacial"] != "voronoi"
