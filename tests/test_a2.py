"""A2 DemoAnalyst — VERIFIER GATE (Steinberger loop).

BENCHMARK FIXO: não altere este arquivo para “fazer passar”.
Só edite `agents/a2_demo_analyst.py` até:

  pytest tests/test_a2.py -q --tb=short -x

sair com código 0 (6 passed).

Contrato: A2 = BaseAgent determinístico (sem LLM) que roda a macro IBGE
`analise_demografica_completa` e grava `analise_demografica` no state com
`insights` derivados em Python. Degrada limpo (score None) em erro.
"""
from __future__ import annotations

import asyncio

from google.adk.agents import BaseAgent

import agents.a2_demo_analyst as a2
from agents.a2_demo_analyst import (
    DemoAnalystAgent,
    _insights_deterministicos,
    _loc_do_state,
    demo_analyst_agent,
)


def test_a2_e_baseagent_sem_llm():
    assert isinstance(demo_analyst_agent, BaseAgent)
    assert isinstance(demo_analyst_agent, DemoAnalystAgent)
    assert getattr(demo_analyst_agent, "model", None) is None
    assert demo_analyst_agent.name == "DemoAnalyst"


def test_a2_loc_do_state_input_params_e_market_context():
    assert _loc_do_state(
        {"input_params": {"cidade": "Fortaleza", "uf": "CE", "bairro": "Cocó"}}
    ) == ("Fortaleza", "CE", "Cocó")
    assert _loc_do_state(
        {"market_context": {"market_context": {"cidade": "Recife", "uf": "PE", "bairro": "Boa Viagem"}}}
    ) == ("Recife", "PE", "Boa Viagem")
    assert _loc_do_state({"input_params": {"cidade": "X", "uf": "CE"}})[2] is None


def test_a2_insights_deterministicos_derivam_dos_numeros():
    r = {"publico_potencial_fitness": 12500, "renda_bairro": 4952.0,
         "score_demografico": 8.0, "classificacao": "EXCELENTE"}
    ins = _insights_deterministicos(r)
    assert any("12.500" in i for i in ins)
    assert any("suporta mensalidade premium" in i for i in ins)
    assert any("8.0/10" in i and "excelente" in i for i in ins)


def test_a2_insights_vazio_sem_dados():
    assert _insights_deterministicos({}) == []


def _fake_macro(cidade, uf, faixa="18-45", bairro=None):
    return {
        "score_demografico": 7.5,
        "publico_potencial_fitness": 10000,
        "renda_bairro": 4000.0,
        "classificacao": "BOM",
    }


def _run_delta(state: dict, monkeypatch) -> dict:
    """Roda o agente offline e devolve o único state_delta."""
    monkeypatch.setattr(a2, "analise_demografica_completa", _fake_macro)
    monkeypatch.setenv("A2_FONTE", "rest")  # pula cross-query censo_setor (offline)
    monkeypatch.setattr(
        "tools.perfil_sexo_idade_tools.perfil_sexo_publico_fitness",
        lambda *a, **k: None,
    )

    class _Session:
        pass

    sess = _Session()
    sess.state = state

    class _Ctx:
        invocation_id = "inv-a2"
        session = sess

    async def _go():
        events = []
        async for e in demo_analyst_agent._run_async_impl(_Ctx()):  # type: ignore[arg-type]
            events.append(e)
        return events

    events = asyncio.run(_go())
    assert len(events) == 1
    return events[0].actions.state_delta


def test_a2_grava_analise_demografica_com_insights(monkeypatch):
    delta = _run_delta(
        {"input_params": {"cidade": "Pirapora", "uf": "MG", "bairro": "Centro"}},
        monkeypatch,
    )
    r = delta["analise_demografica"]
    assert r["score_demografico"] == 7.5
    assert isinstance(r.get("insights"), list) and r["insights"]


def test_a2_degrada_limpo_com_score_none(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("IBGE fora do ar")

    monkeypatch.setattr(a2, "analise_demografica_completa", _boom)
    monkeypatch.setenv("A2_FONTE", "rest")

    class _Session:
        pass

    sess = _Session()
    sess.state = {"input_params": {"cidade": "X", "uf": "CE"}}

    class _Ctx:
        invocation_id = "inv-a2-erro"
        session = sess

    async def _go():
        return [e async for e in demo_analyst_agent._run_async_impl(_Ctx())]  # type: ignore[arg-type]

    events = asyncio.run(_go())
    delta = events[0].actions.state_delta
    assert delta["analise_demografica"]["score_demografico"] is None
