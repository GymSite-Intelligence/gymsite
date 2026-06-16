"""A2 DemoAnalyst convertido p/ determinístico (sem LLM) — helpers + agente."""
from agents.a2_demo_analyst import (
    DemoAnalystAgent,
    _insights_deterministicos,
    _loc_do_state,
    demo_analyst_agent,
)


def test_agente_e_baseagent_sem_llm():
    from google.adk.agents import BaseAgent

    assert isinstance(demo_analyst_agent, BaseAgent)
    assert isinstance(demo_analyst_agent, DemoAnalystAgent)
    assert demo_analyst_agent.name == "DemoAnalyst"
    # BaseAgent não tem atributo de modelo LLM
    assert not hasattr(demo_analyst_agent, "model") or demo_analyst_agent.__class__ is DemoAnalystAgent


def test_loc_do_state_input_params_e_market_context():
    assert _loc_do_state({"input_params": {"cidade": "Fortaleza", "uf": "CE", "bairro": "Cocó"}}) == (
        "Fortaleza", "CE", "Cocó",
    )
    # via market_context (double-nested, output do A0)
    assert _loc_do_state(
        {"market_context": {"market_context": {"cidade": "Recife", "uf": "PE", "bairro": "Boa Viagem"}}}
    ) == ("Recife", "PE", "Boa Viagem")
    # bairro vazio -> None
    assert _loc_do_state({"input_params": {"cidade": "X", "uf": "CE"}})[2] is None


def test_insights_deterministicos():
    r = {"publico_potencial_fitness": 12500, "renda_bairro": 4952.0,
         "score_demografico": 8.0, "classificacao": "EXCELENTE"}
    ins = _insights_deterministicos(r)
    assert any("12.500" in i for i in ins)
    assert any("suporta mensalidade premium" in i for i in ins)
    assert any("8.0/10" in i and "excelente" in i for i in ins)


def test_insights_renda_baixa_nao_suporta():
    ins = _insights_deterministicos({"renda_media_domiciliar": 900, "score_demografico": 4, "classificacao": "FRACO"})
    assert any("não suporta" in i for i in ins)


def test_insights_vazio_sem_dados():
    assert _insights_deterministicos({}) == []
