"""A5 ContactHunter — VERIFIER GATE (Steinberger loop).

BENCHMARK FIXO: não altere este arquivo para “fazer passar”.
Só edite `agents/a5_contact_hunter.py` até:

  python -m pytest tests/test_a5.py -q --tb=short -x

sair com código 0 (5 passed).

Contrato: A5 é um BaseAgent determinístico, sem LLM, destinado à prospecção e
fora do pipeline de viabilidade. Executa `gerar_contato_decisor_completo` com
o state real e grava somente `contato_decisor`. Falhas não interrompem o fluxo.
"""
from __future__ import annotations

import asyncio
import types

from google.adk.agents import BaseAgent

import agents.a5_contact_hunter as a5


def _run(state: dict) -> list:
    ctx = types.SimpleNamespace(
        session=types.SimpleNamespace(state=state),
        invocation_id="inv-a5",
    )

    async def _go():
        return [event async for event in a5.contact_hunter_agent._run_async_impl(ctx)]

    return asyncio.run(_go())


def test_a5_e_baseagent_sem_llm():
    assert isinstance(a5.contact_hunter_agent, BaseAgent)
    assert isinstance(a5.contact_hunter_agent, a5.ContactHunterAgent)
    assert getattr(a5.contact_hunter_agent, "model", None) is None
    assert a5.contact_hunter_agent.name == "ContactHunter"


def test_a5_state_shim_expoe_o_state_real():
    state = {"candidatos_geoscout_pronto": {"candidatos": []}}
    shim = a5._StateShim(state)
    assert shim.state is state
    assert set(a5._StateShim.__slots__) == {"state"}


def test_a5_grava_somente_contato_decisor(monkeypatch):
    state = {"candidatos_geoscout_pronto": {"candidatos": [{"nome": "Ponto A"}]}}
    captured: dict = {}
    expected = {
        "decisor": "Responsável comercial",
        "canal_recomendado": "WhatsApp",
        "script_abordagem": "Olá",
    }

    def _macro(tool_context):
        captured["state"] = tool_context.state
        return expected

    monkeypatch.setattr(a5, "gerar_contato_decisor_completo", _macro)
    events = _run(state)

    assert len(events) == 1
    assert captured["state"] is state
    assert events[0].actions.state_delta == {"contato_decisor": expected}


def test_a5_macro_nao_dict_grava_objeto_vazio(monkeypatch):
    monkeypatch.setattr(
        a5,
        "gerar_contato_decisor_completo",
        lambda tool_context: "resultado inválido",
    )
    delta = _run({})[0].actions.state_delta
    assert delta == {"contato_decisor": {}}


def test_a5_macro_falha_degrada_sem_interromper(monkeypatch):
    def _boom(tool_context):
        raise RuntimeError("fonte de contato indisponível")

    monkeypatch.setattr(a5, "gerar_contato_decisor_completo", _boom)
    events = _run({})

    assert len(events) == 1
    result = events[0].actions.state_delta["contato_decisor"]
    assert "fonte de contato indisponível" in result["erro"]
