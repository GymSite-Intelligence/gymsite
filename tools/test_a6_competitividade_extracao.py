"""Fallback A3a → concorrentes_detalhados + score no extract A6."""
from agents.a6_report_consolidator import (
    _alinhar_markdown_ao_estruturado,
    _resolver_competitividade_extracao,
    _slim_concorrente,
)


def test_post_check_saturacao_corrige_over_statement():
    """Safety net A6 flash: narrativa 'SATURADO/extrema' vira o nível real quando BAIXO/MEDIO."""
    txt = "O mercado competitivo é **SATURADO**. Há extrema saturação e saturação alta."
    baixo = _alinhar_markdown_ao_estruturado(txt, {"nivel_saturacao": "BAIXO"})
    assert "SATURADO" not in baixo and "extrema satura" not in baixo.lower()
    assert "baixa saturação competitiva" in baixo
    # nível ALTO/SATURADO não é rebaixado
    alto_txt = "mercado SATURADO real"
    assert _alinhar_markdown_ao_estruturado(alto_txt, {"nivel_saturacao": "SATURADO"}) == alto_txt


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


def test_alinhar_markdown_scores_em_dash_c908():
    """Split-brain c908: LLM emitiu — ; estruturado tem números — md deve sincronizar."""
    md = """## 📈 Scores Regionais

| Dimensão | Score (0-10) | Classificação |
|---|---|---|
| Demográfico | — | — |
| Competitivo | — | — |
| Viabilidade financeira | — | — |

**Transparência (OBRIGATÓRIO):**
- `Concorrentes na praça (raio 1 km): — — saturação —`
- `Retorno bruto da busca (contexto): — resultados — não redefine a saturação`

**Score Bairro:** — — indicador macro
**Score Top 1 Candidato:** — — — base do veredito

---

## 🏆 Top 3 Candidatos
Não há candidatos a imóveis para análise.

---

## 🏗️ Checklist de Diligência do Imóvel
x
"""
    out = {
        "score_bairro": 5.64,
        "score_top1_candidato": 5.98,
        "score_concorrencia": 1.91,
        "scores_regionais": {"demografico": 10.0, "competitivo": 1.91, "viabilidade": 5.0},
        "nivel_saturacao": "MEDIO",
        "total_concorrentes_analisados": 4,
        "total_encontrados_raio": 12,
        "top_3_candidatos": [
            {
                "nome": "Empório de Fátima Delicatessen",
                "endereco": "Av. Oswaldo Studart, 250 - Fátima",
                "tipo": "bakery",
                "area_estimada_m2": 1200,
                "score_geoscout": 7.0,
                "score_ancoragem": 10.0,
                "motivo": "Supermercado em avenida principal",
                "estimativa_visibilidade": "alta",
                "qualidade_sinal": "indireto-heuristico",
                "polos_geradores": [],
            }
        ],
    }
    fixed = _alinhar_markdown_ao_estruturado(md, out)
    assert "| Demográfico | 10 | forte |" in fixed
    assert "| Competitivo | 1.91 | MEDIO |" in fixed
    assert "| Viabilidade financeira | 5 | moderado |" in fixed
    assert "**Score Bairro:** 5.64" in fixed
    assert "**Score Top 1 Candidato:** 5.98" in fixed
    assert "Concorrentes na praça (raio 1 km): 4" in fixed
    assert "saturação MEDIO" in fixed
    assert "Retorno bruto da busca (contexto): 12" in fixed
    assert "Não há candidatos" not in fixed
    assert "Empório de Fátima" in fixed
    assert "Score GeoScout:** 7" in fixed


def test_render_top3_vazio():
    from agents.a6_report_consolidator import _renderizar_md_top3_candidatos

    assert "Não há candidatos" in _renderizar_md_top3_candidatos([])
