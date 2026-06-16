"""Testes — A3a CompetitorSearch determinístico (sem LLM). Macro stubada, sem rede."""
from __future__ import annotations

import asyncio
import types

import agents.a3a_competitor_search as m


def _fake_ctx(state: dict) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        session=types.SimpleNamespace(state=state), invocation_id="inv-1"
    )


def _run(agent, ctx) -> list:
    async def _go():
        return [e async for e in agent._run_async_impl(ctx)]

    return asyncio.run(_go())


def test_extrai_bairro_cidade_aninhado():
    state = {"market_context": {"market_context": {"bairro": "Cocó", "cidade": "Fortaleza"}}}
    assert m._extrair_bairro_cidade(state) == ("Cocó", "Fortaleza")


def test_extrai_bairro_cidade_topo_do_state():
    state = {"bairro": "Aldeota", "cidade": "Fortaleza"}
    assert m._extrair_bairro_cidade(state) == ("Aldeota", "Fortaleza")


def test_emite_event_com_state_delta(monkeypatch):
    captura: dict = {}

    async def _stub(tool_context, bairro, cidade):
        captura.update(bairro=bairro, cidade=cidade, state=tool_context.state)
        return {"concorrentes_brutos": [{"nome": "X"}], "redes_a0_cobertas": ["Smart Fit"]}

    monkeypatch.setattr(m, "analisar_concorrentes_a3a_completo", _stub)
    state = {"market_context": {"bairro": "Cocó", "cidade": "Fortaleza"}}
    evs = _run(m.competitor_search_agent, _fake_ctx(state))

    assert len(evs) == 1
    e = evs[0]
    assert e.author == "CompetitorSearch"
    assert captura["bairro"] == "Cocó" and captura["cidade"] == "Fortaleza"
    assert captura["state"] is state  # shim expõe o state real (escritas propagam)
    delta = e.actions.state_delta
    assert list(delta) == ["concorrentes_brutos"]
    assert delta["concorrentes_brutos"]["concorrentes_brutos"] == [{"nome": "X"}]


def test_macro_falha_nao_derruba_pipeline(monkeypatch):
    async def _boom(tool_context, bairro, cidade):
        raise RuntimeError("places down")

    monkeypatch.setattr(m, "analisar_concorrentes_a3a_completo", _boom)
    evs = _run(m.competitor_search_agent, _fake_ctx({"bairro": "X", "cidade": "Y"}))

    assert len(evs) == 1
    payload = evs[0].actions.state_delta["concorrentes_brutos"]
    assert payload["concorrentes_brutos"] == []  # A3b lida com lista vazia
    assert "places down" in payload["erro"]
