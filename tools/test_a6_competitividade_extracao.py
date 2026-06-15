"""Fallback A3a → concorrentes_detalhados + score no extract A6."""
from agents.a6_report_consolidator import (
    _alinhar_markdown_ao_estruturado,
    _resolver_competitividade_extracao,
    _slim_concorrente,
)


def test_slim_concorrente_corta_campos_pesados():
    """Slim dropa grounding cru + reviews duplicadas + cap 5 reviews; mantém o report."""
    c = {
        "nome": "Academia X", "rating_oficial": 4.5, "num_avaliacoes": 200,
        "enrichment_search_grounding_text": "L" * 1500,
        "reviews_traduzidas": [{"a": 1}] * 5,
        "atividade_marketing": {"posts": ["p" * 500]},
        "reviews": [{"rating": 1, "quote_curta": "Q" * 300, "categoria_dor": "atendimento",
                     "sinal": "negativo", "extra": "y" * 200}] * 8,
    }
    s = _slim_concorrente(c)
    assert "enrichment_search_grounding_text" not in s
    assert "reviews_traduzidas" not in s and "atividade_marketing" not in s
    assert s["nome"] == "Academia X" and s["rating_oficial"] == 4.5  # report-relevante mantido
    assert len(s["reviews"]) == 5 and len(s["reviews"][0]["quote_curta"]) == 180
    assert "extra" not in s["reviews"][0]                            # review enxuta


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
