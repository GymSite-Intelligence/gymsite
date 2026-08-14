"""RN-A9-014/015: A4 nenhum → A9 INDETERMINADO sem ticket."""

from agents.a9_positioning_strategist import _build_errc_indeterminado, _errc_deterministica


def test_build_errc_indeterminado_sem_ticket():
    out = _build_errc_indeterminado(
        {"market_context": {"bairro": "Coco", "cidade": "Fortaleza", "uf": "CE"}},
        motivo="A4 sem modelo viável (alerta: todos_cenarios_inviaveis)",
        fonte_veredito="a4_sem_modelo_viavel",
    )
    assert out["veredito_posicionamento"] == "INDETERMINADO"
    assert out["fonte_veredito"] == "a4_sem_modelo_viavel"
    assert out["recomendacao_ticket"]["ticket_recomendado"] is None
    assert out["recomendacao_ticket"]["confianca"] == "indisponivel"
    assert out["modelo_a4"] == "nenhum"


def test_errc_degrada_quando_a4_nenhum():
    state = {
        "analise_financeira": {
            "modelo_recomendado": "nenhum",
            "recomendacao_modelo": "nenhum",
            "alerta_viabilidade": "todos_cenarios_inviaveis",
            "cenarios": {
                "low": {"viabilidade": "INVIAVEL", "modelo": "Low Cost"},
                "mid": {"viabilidade": "INVIAVEL", "modelo": "Mid Market"},
                "premium": {"viabilidade": "INVIAVEL", "modelo": "Premium"},
            },
        },
        "input_params": {"cidade": "Fortaleza", "bairro": "Coco", "uf": "CE"},
    }
    out = _errc_deterministica(state)
    assert out["veredito_posicionamento"] == "INDETERMINADO"
    assert out["fonte_veredito"] == "a4_sem_modelo_viavel"
    assert out["recomendacao_ticket"]["ticket_recomendado"] is None
    assert out["recomendacao_ticket"]["confianca"] == "indisponivel"
