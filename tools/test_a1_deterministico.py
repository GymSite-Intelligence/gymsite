"""A1 GeoScout determinístico — listing filtrado + MRLR."""
import asyncio

from google.adk.agents import BaseAgent

from agents.a1_geoscout import GeoScoutAgent, geoscout_agent, _loc_do_state
import agents.a1_geoscout as a1


def test_a1_e_baseagent_sem_llm():
    assert isinstance(geoscout_agent, BaseAgent)
    assert isinstance(geoscout_agent, GeoScoutAgent)
    assert getattr(geoscout_agent, "model", None) is None


def test_loc_do_state_input_params():
    c, u, b = _loc_do_state(
        {"input_params": {"cidade": "Fortaleza", "uf": "CE", "bairro": "Cocó"}}
    )
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


def test_listing_mrlr_duas_chaves(monkeypatch):
    fake = {
        "status": "ok",
        "total_candidatos": 1,
        "candidatos": [{"qualidade_sinal": "direto-listing-bairro"}],
    }
    monkeypatch.setattr(
        a1,
        "buscar_candidatos_listing_mrlr",
        lambda **kwargs: fake,
    )
    ev = _run({"input_params": {"cidade": "Pirapora", "uf": "MG", "bairro": "Centro"}})
    d = ev.actions.state_delta
    assert d["candidatos_geoscout_pronto"]["status"] == "ok"
    assert d["candidatos_geoscout"]["total_candidatos"] == 1
    assert d["candidatos_geoscout_pronto"] is d["candidatos_geoscout"]


def test_listing_falha_degrada_vazio(monkeypatch):
    monkeypatch.setattr(
        a1,
        "buscar_candidatos_listing_mrlr",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("indisponível")),
    )
    ev = _run({})
    d = ev.actions.state_delta
    assert d["candidatos_geoscout"]["candidatos"] == []
    assert d["candidatos_geoscout"]["status"] == "ok_vazio"
