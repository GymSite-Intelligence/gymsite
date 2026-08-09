"""A9 PositioningStrategist — VERIFIER GATE (Steinberger loop).

BENCHMARK FIXO: não altere este arquivo para "fazer passar".
Só edite `agents/a9_positioning_strategist.py` até:

  python -m pytest tests/test_a9.py -q --tb=short -x

sair com código 0 (7 passed).

Contrato: A9 é `BaseAgent` DETERMINÍSTICO (sem LLM). A ERRC, veredito, ticket,
GAPs e mapa de serviços nascem da matéria-prima já calculada (headroom de renda
IBGE Censo 2022 + oferta real dos concorrentes). Nenhum número/serviço é inventado:
gap só existe quando NINGUÉM da praça anuncia; sem local resolvível → INDETERMINADO.
"""
from __future__ import annotations

from google.adk.agents import Agent, BaseAgent

import agents.a9_positioning_strategist as a9


def test_a9_contrato_do_agente_e_deterministico():
    agent = a9.positioning_strategist_agent
    assert isinstance(agent, a9.PositioningStrategistAgent)
    assert isinstance(agent, BaseAgent)
    # É determinístico: NÃO é LlmAgent e não carrega model.
    assert not isinstance(agent, Agent)
    assert getattr(agent, "model", None) is None
    assert agent.name == "PositioningStrategist"
    assert getattr(agent, "after_agent_callback", None) is a9._a9_after_agent_callback


def test_a9_errc_monta_estrutura_e_markdown():
    state = {
        "input_params": {"cidade": "Pirapora", "uf": "MG", "bairro": "Centro"},
        "inteligencia_competitiva": {
            "concorrentes_detalhados": [
                {
                    "nome": "Academia Alpha",
                    "planos_precos": [
                        {"plano": "Mensal", "inclui": ["Musculação"], "preco_mensal": 120}
                    ],
                }
            ],
            "nivel_saturacao": "MEDIO",
        },
    }
    out = a9._errc_deterministica(state)
    assert out["fonte_geracao"] == "deterministico_errc"
    for dim in ("eliminar", "reduzir", "aumentar", "criar"):
        assert out["framework_errc"][dim]
    assert out["mapa_servicos"]
    assert isinstance(out["recomendacao_ticket"], dict)
    md = out["markdown"]
    for marco in ("Framework ERRC", "ELIMINAR", "REDUZIR", "AUMENTAR", "CRIAR"):
        assert marco in md


def test_a9_gap_so_existe_quando_ninguem_anuncia():
    state = {
        "inteligencia_competitiva": {
            "concorrentes_detalhados": [
                {"nome": "Alpha", "planos_precos": [{"plano": "M", "inclui": ["Musculação"]}]}
            ]
        }
    }
    gaps = a9._gaps_reais(state)
    assert gaps is not None
    assert "Musculação" not in gaps           # alguém anuncia → não é gap
    assert "Nutrição integrada" in gaps       # ninguém anuncia → é gap


def test_a9_sem_concorrentes_nao_inventa_gap():
    assert a9._gaps_reais({}) is None


def test_a9_base_penetracao_e_a_praca_inteira_com_dedupe():
    state = {
        "inteligencia_competitiva": {
            "concorrentes_detalhados": [{"nome": "Smart Fit - Centro"}],
            "academias_analisadas": [{"nome": "Smart Fit - Centro"}, {"nome": "TBOX"}],
            "top_independentes": [{"nome": "Studio Zen"}],
        }
    }
    nomes = [c["nome"] for c in a9._concorrentes_para_oferta(state)]
    assert len(nomes) == 3
    assert nomes.count("Smart Fit - Centro") == 1


def test_a9_sem_local_veredito_indeterminado_e_nao_quebra():
    out = a9._errc_deterministica({})
    assert out["veredito_posicionamento"] == "INDETERMINADO"
    assert isinstance(out["markdown"], str) and out["markdown"]
    assert out["fonte_geracao"] == "deterministico_errc"


def test_a9_ressalva_indeterminado_e_idempotente():
    base = "Recomenda modelo Mid Market."
    uma_vez = a9._emendar_ressalva(base)
    assert a9._RESSALVA_INDETERMINADO in uma_vez
    # append idempotente: aplicar de novo não duplica a ressalva.
    assert a9._emendar_ressalva(uma_vez) == uma_vez
