"""A1 GeoScout — VERIFIER GATE (Steinberger loop).

BENCHMARK FIXO: não altere este arquivo para “fazer passar”.
Só edite `agents/a1_geoscout.py` até:

  pytest tests/test_a1.py -q --tb=short -x

sair com código 0 (4 passed).

Contrato 2026-08-05: macro `analisar_pontos_comerciais_completo` MORTA no
caminho A1. A1 usa só listing SearchAPI filtrado + MRLR.
"""
from __future__ import annotations

import asyncio

from google.adk.agents import BaseAgent

from agents.a1_geoscout import GeoScoutAgent, _loc_do_state, geoscout_agent
import agents.a1_geoscout as a1


def test_a1_e_baseagent_sem_llm():
    assert isinstance(geoscout_agent, BaseAgent)
    assert isinstance(geoscout_agent, GeoScoutAgent)
    assert getattr(geoscout_agent, "model", None) is None


def test_a1_nome_geoscout():
    assert geoscout_agent.name == "GeoScout"


def test_a1_loc_do_state_input_params_e_market_context():
    st = {
        "input_params": {"cidade": "Fortaleza", "uf": "CE", "bairro": "Cocó"},
        "market_context": {"market_context": {"cidade": "X", "uf": "YY", "bairro": "Z"}},
    }
    cidade, uf, bairro = _loc_do_state(st)
    assert cidade == "Fortaleza"
    assert uf == "CE"
    assert bairro == "Cocó"


def test_a1_grava_listing_mrlr_nas_duas_chaves(monkeypatch):
    calls: list[dict] = []
    fake = {
        "status": "ok",
        "total_candidatos": 1,
        "candidatos": [
            {
                "nome": "Galpão Centro",
                "qualidade_sinal": "direto-listing-bairro",
                "aluguel_fonte": "MRLR",
            }
        ],
        "fonte": "listing_cascata_searchapi+mrlr",
    }

    def _listing(**kwargs):
        calls.append(kwargs)
        return fake

    monkeypatch.setattr(a1, "buscar_candidatos_listing_mrlr", _listing)

    class _Session:
        state: dict = {
            "input_params": {"cidade": "Pirapora", "uf": "MG", "bairro": "Centro"}
        }

    class _Ctx:
        invocation_id = "inv-a1-listing"
        session = _Session()

    async def _run():
        events = []
        async for e in geoscout_agent._run_async_impl(_Ctx()):  # type: ignore[arg-type]
            events.append(e)
        return events

    events = asyncio.run(_run())
    assert calls == [
        {
            "cidade": "Pirapora",
            "uf": "MG",
            "bairro": "Centro",
            "area_m2_min": 500,
            "area_m2_max": 5000,
        }
    ]
    assert len(events) == 1
    delta = events[0].actions.state_delta
    pronto = delta["candidatos_geoscout_pronto"]
    legado = delta["candidatos_geoscout"]
    assert pronto is legado
    assert pronto["status"] == "ok"
    assert pronto["total_candidatos"] == 1
    assert pronto["candidatos"][0]["qualidade_sinal"] == "direto-listing-bairro"
    assert pronto["candidatos"][0]["aluguel_fonte"] == "MRLR"
