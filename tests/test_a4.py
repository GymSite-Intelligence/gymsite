"""A4 FinancialEstimator — VERIFIER GATE (Steinberger loop).

BENCHMARK FIXO: não altere este arquivo para “fazer passar”.
Só edite `agents/a4_financial_estimator.py` até:

  pytest tests/test_a4.py -q --tb=short -x

sair com código 0 (7 passed).

Contrato: A4 = BaseAgent determinístico (sem LLM). Roda a macro async
`analise_financeira_a4_completo` (aluguel = MRLR Tier 0, canônico), monta
`justificativa` por template e grava `analise_financeira_pronto` +
`analise_financeira` (mesmo dict) no state. Degrada limpo (score None) em erro.
"""
from __future__ import annotations

import asyncio
import types

from google.adk.agents import BaseAgent

import agents.a4_financial_estimator as a4
from agents.a4_financial_estimator import (
    _derivar_area,
    _justificativa_det,
    _top1_latlng,
    financial_estimator_agent,
)


def _ctx(state: dict) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        session=types.SimpleNamespace(state=state), invocation_id="inv-a4"
    )


def _run(ctx) -> list:
    async def _go():
        return [e async for e in financial_estimator_agent._run_async_impl(ctx)]

    return asyncio.run(_go())


# ── Contrato estático ─────────────────────────────────────────────────────────

def test_a4_e_baseagent_sem_llm():
    assert isinstance(financial_estimator_agent, BaseAgent)
    assert getattr(financial_estimator_agent, "model", None) is None
    assert financial_estimator_agent.name == "FinancialEstimator"


# ── Helpers determinísticos ───────────────────────────────────────────────────

def test_a4_area_da_media_e_default():
    assert _derivar_area({"area_m2_min": 800, "area_m2_max": 1500}, "academia") == 1150.0
    assert _derivar_area({}, "studio_pilates") == 215.0


def test_a4_justificativa_template_com_nota_genero():
    r = {"recomendacao_modelo": "Mid Market",
         "cenarios": {"m": {"modelo": "Mid Market", "margem_percentual": 39, "payback_meses": 17}}}
    j = _justificativa_det(r, "Cocó", "predominantemente_feminino")
    assert "Mid Market" in j and "39%" in j and "17m" in j
    assert "Pilates" in j


def test_a4_top1_latlng():
    st = {"candidatos_geoscout_pronto": {"candidatos": [{"lat": -3.7, "lng": -38.5}]}}
    assert _top1_latlng(st) == (-3.7, -38.5)
    assert _top1_latlng({}) == (None, None)


# ── Contrato de saída: grava as duas chaves com justificativa ─────────────────

def _fake_state() -> dict:
    return {
        "input_params": {
            "cidade": "Fortaleza", "uf": "CE", "bairro": "Cocó",
            "tipo_negocio": "academia", "genero_alvo": "predominantemente_feminino",
            "area_m2_min": 1000, "area_m2_max": 1500,
        }
    }


def test_a4_grava_duas_chaves_com_justificativa(monkeypatch):
    capturado: dict = {}

    async def _macro(bairro, cidade, uf, area_m2, **kw):
        capturado.update(bairro=bairro, cidade=cidade, uf=uf, area_m2=area_m2, kw=kw)
        return {
            "recomendacao_modelo": "Mid Market",
            "score_viabilidade": 7.2,
            "cenarios": {"m": {"modelo": "Mid Market", "margem_percentual": 39, "payback_meses": 17}},
        }

    monkeypatch.setattr(a4, "analise_financeira_a4_completo", _macro)
    evs = _run(_ctx(_fake_state()))
    assert len(evs) == 1
    delta = evs[0].actions.state_delta
    pronto = delta["analise_financeira_pronto"]
    legado = delta["analise_financeira"]
    assert pronto is legado
    assert pronto["score_viabilidade"] == 7.2
    assert "Mid Market" in pronto["justificativa"]
    assert capturado["cidade"] == "Fortaleza" and capturado["bairro"] == "Cocó"


def test_a4_macro_nao_dict_degrada(monkeypatch):
    async def _macro(*a, **k):
        return "erro-string"

    monkeypatch.setattr(a4, "analise_financeira_a4_completo", _macro)
    delta = _run(_ctx(_fake_state()))[0].actions.state_delta
    assert delta["analise_financeira_pronto"]["score_viabilidade"] is None


def test_a4_macro_falha_degrada_limpo(monkeypatch):
    async def _boom(*a, **k):
        raise RuntimeError("MRLR indisponível")

    monkeypatch.setattr(a4, "analise_financeira_a4_completo", _boom)
    delta = _run(_ctx(_fake_state()))[0].actions.state_delta
    r = delta["analise_financeira_pronto"]
    assert r["score_viabilidade"] is None
    assert "MRLR indisponível" in r["erro"]
    assert delta["analise_financeira"] is r
