"""INDETERMINADO preenche Eliminar/Reduzir/Aumentar via dores + demografia."""
from agents.a9_positioning_strategist import _build_errc_indeterminado


def test_errc_indeterminado_com_dores():
    state = {
        "cidade": "Fortaleza",
        "bairro": "Meireles",
        "uf": "CE",
        "input_params": {
            "cidade": "Fortaleza",
            "bairro": "Meireles",
            "uf": "CE",
            "publico_alvo": "40-59",
        },
        "inteligencia_competitiva": {
            "inteligencia_competitiva": {
                "dores_dominantes": [
                    {"dor": "atendimento_ruim", "mencoes": 4},
                    {"dor": "equipamento_problema", "mencoes": 3},
                    {"dor": "climatizacao", "mencoes": 1},
                ],
            }
        },
        "demografia_bairro": {
            "perfil_idade_sexo_bairro": {
                "segmentos": {
                    "25-39": {
                        "total": 8573, "mulheres": 4687, "homens": 3886,
                        "pct_mulheres": 54.7, "pct_homens": 45.3,
                    },
                    "40-59": {
                        "total": 12326, "mulheres": 7013, "homens": 5313,
                        "pct_mulheres": 56.9, "pct_homens": 43.1,
                    },
                    "60+": {
                        "total": 9843, "mulheres": 5748, "homens": 4095,
                        "pct_mulheres": 58.4, "pct_homens": 41.6,
                    },
                }
            }
        },
    }

    out = _build_errc_indeterminado(
        state,
        motivo="A4 sem modelo viável (alerta: todos_cenarios_inviaveis)",
        fonte_veredito="a4_sem_modelo_viavel",
    )
    errc = out["framework_errc"]

    assert len(errc["eliminar"]) >= 2
    assert any("atendimento" in b.lower() for b in errc["eliminar"])
    assert len(errc["aumentar"]) >= 3
    assert any("equipamento" in b.lower() or "climatiz" in b.lower() for b in errc["aumentar"])
    assert any("longevidade" in b.lower() for b in errc["aumentar"])
    assert len(errc["reduzir"]) >= 2
    assert "criar" in errc
    assert "dores dominantes" in out["markdown"].lower()
    assert out["recomendacao_ticket"]["ticket_recomendado"] is None


def test_errc_indeterminado_sem_dores():
    out = _build_errc_indeterminado(
        {
            "cidade": "Fortaleza",
            "bairro": "Teste",
            "uf": "CE",
            "input_params": {},
            "inteligencia_competitiva": {},
            "demografia_bairro": {},
        },
        motivo="teste",
        fonte_veredito="teste",
    )
    errc = out["framework_errc"]
    assert len(errc["eliminar"]) >= 1
    assert len(errc["reduzir"]) >= 2
    assert len(errc["aumentar"]) >= 1
    assert not any("atendimento" in b.lower() for b in errc["eliminar"])


def test_errc_indeterminado_dores_no_consolidado():
    out = _build_errc_indeterminado(
        {
            "input_params": {"cidade": "Fortaleza", "bairro": "Meireles", "uf": "CE"},
            "output_consolidado": {
                "dores_dominantes": [
                    {"dor": "atendimento_ruim", "mencoes": 4},
                    {"dor": "equipamento_problema", "mencoes": 3},
                ],
            },
        },
        motivo="A4 sem modelo viável",
        fonte_veredito="a4_sem_modelo_viavel",
    )
    errc = out["framework_errc"]
    assert any("atendimento" in b.lower() for b in errc["eliminar"])
    assert any("equipamento" in b.lower() or "climatiz" in b.lower() for b in errc["aumentar"])


def test_errc_indeterminado_cria_24h_se_ninguem_oferece():
    out = _build_errc_indeterminado(
        {
            "input_params": {"cidade": "Fortaleza", "bairro": "Meireles", "uf": "CE"},
            "output_consolidado": {
                "competitors_set": [
                    {"nome": "A", "tem_24h": False},
                    {"nome": "B", "tem_24h": False},
                    {"nome": "C", "tem_24h": False},
                ],
            },
        },
        motivo="A4 sem modelo viável",
        fonte_veredito="a4_sem_modelo_viavel",
    )
    criar = out["framework_errc"]["criar"]
    assert any("24h" in str(x).lower() for x in criar)


def test_errc_indeterminado_nao_cria_24h_se_alguem_oferece():
    out = _build_errc_indeterminado(
        {
            "input_params": {"cidade": "Fortaleza", "bairro": "Meireles", "uf": "CE"},
            "output_consolidado": {
                "competitors_set": [
                    {"nome": "A", "tem_24h": False},
                    {"nome": "B", "tem_24h": True},
                ],
            },
        },
        motivo="A4 sem modelo viável",
        fonte_veredito="a4_sem_modelo_viavel",
    )
    criar = out["framework_errc"]["criar"]
    assert not any("24h" in str(x).lower() for x in criar)
