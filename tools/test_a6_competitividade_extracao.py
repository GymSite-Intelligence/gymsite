"""Fallback A3a → concorrentes_detalhados + score no extract A6."""
from agents.a6_report_consolidator import (
    _alinhar_markdown_ao_estruturado,
    _resolver_competitividade_extracao,
)


def test_fallback_concorrentes_brutos_recalcula_score():
    brutos = [
        {
            "nome": "Arena Champions",
            "rating_geral": 4.7,
            "num_avaliacoes": 100,
            "place_id": "ChIJ_test",
        },
        {
            "nome": "Smart Fit",
            "rating_geral": 4.3,
            "num_avaliacoes": 50,
        },
    ]
    comp = _resolver_competitividade_extracao(
        ic_raw={},
        inner_ic={},
        cs_raw={
            "concorrentes_brutos": brutos,
            "total_encontrados_raio": 10,
        },
    )
    assert len(comp["concorrentes_detalhados"]) == 2
    assert comp["fonte_fallback"] == "concorrentes_brutos_a3a"
    assert comp["score_concorrencia"] is not None
    assert comp["total_concorrentes_analisados"] == 2


def test_guard_nao_dispara_com_brutos():
    comp = _resolver_competitividade_extracao(
        ic_raw={},
        inner_ic={},
        cs_raw={"concorrentes_brutos": [{"nome": "Gym", "rating_geral": 4.0}]},
    )
    sem = (not comp["concorrentes_detalhados"]) and comp["total_concorrentes_analisados"] == 0
    assert sem is False


def test_alinhar_markdown_veredito():
    md = "## 📌 Decisão Recomendada\n**INVESTIGAR MAIS.**\n\n**Score Bairro:** 8.75"
    out = {
        "veredito": "APROVADO COM RESSALVAS",
        "score_bairro": 6.5,
        "score_top1_candidato": 6.9,
    }
    fixed = _alinhar_markdown_ao_estruturado(md, out)
    assert "APROVADO COM RESSALVAS" in fixed
    assert "INVESTIGAR MAIS" not in fixed.split("Decisão")[1][:80]
    assert "6.5" in fixed
