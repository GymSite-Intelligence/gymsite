"""A1 GeoScout determinizado (BaseAgent, sem LLM) — roda a macro + grava as 2 chaves."""
import asyncio
from agents.a1_geoscout import GeoScoutAgent, geoscout_agent, _loc_do_state
import agents.a1_geoscout as a1


def test_a1_e_baseagent_sem_llm():
    from google.adk.agents import BaseAgent
    assert isinstance(geoscout_agent, BaseAgent)
    assert isinstance(geoscout_agent, GeoScoutAgent)
    assert getattr(geoscout_agent, "model", None) is None  # sem LLM


def test_loc_do_state_input_params():
    c, u, b = _loc_do_state({"input_params": {"cidade": "Fortaleza", "uf": "CE", "bairro": "Cocó"}})
    assert (c, u, b) == ("Fortaleza", "CE", "Cocó")


class _Sess:
    def __init__(self, state):
        self.state = state


class _Ctx:
    def __init__(self, state):
        self.session = _Sess(state)
        self.invocation_id = "test"


def _run(state):
    async def _go():
        ev = None
        async for e in geoscout_agent._run_async_impl(_Ctx(state)):
            ev = e
        return ev
    return asyncio.run(_go())


def test_macro_grava_duas_chaves(monkeypatch):
    monkeypatch.setattr(a1, "analisar_pontos_comerciais_completo",
                        lambda b, c, u: {"total_candidatos": 3, "candidatos": [{"nome": "X"}]})
    ev = _run({"input_params": {"cidade": "Fortaleza", "uf": "CE", "bairro": "Cocó"}})
    d = ev.actions.state_delta
    assert d["candidatos_geoscout_pronto"]["total_candidatos"] == 3
    assert d["candidatos_geoscout"]["total_candidatos"] == 3  # ambas


def test_macro_erro_degrada(monkeypatch):
    def _boom(*a):
        raise RuntimeError("macro caiu")
    monkeypatch.setattr(a1, "analisar_pontos_comerciais_completo", _boom)
    ev = _run({"input_params": {"cidade": "X", "bairro": "Y"}})
    d = ev.actions.state_delta
    assert d["candidatos_geoscout"]["total_candidatos"] == 0
    assert "erro" in d["candidatos_geoscout"]
