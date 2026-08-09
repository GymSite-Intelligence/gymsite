"""A3 CompetitorSearch (A3a) + CompetitorAnalysis (A3b) — VERIFIER GATE (Steinberger loop).

BENCHMARK FIXO: não altere este arquivo para “fazer passar”.
Só edite `agents/a3a_competitor_search.py` / `agents/a3b_competitor_analysis.py` até:

  pytest tests/test_a3.py -q --tb=short -x

sair com código 0 (9 passed).

Contrato 2026-08-05:
- A3 em produção = par determinístico A3a + A3b (BaseAgent, sem LLM). O LlmAgent
  `a3_competitor_intel.py` (CompetitorIntel) está MORTO (comentado no runner).
- A3a: roda `analisar_concorrentes_a3a_completo`, grava `concorrentes_brutos`.
- A3b: roda `analisar_concorrentes_completo`, grava `inteligencia_competitiva`
  + `oferta_concorrentes`; sintetiza posicionamento/resumo por template.
- Filtro autoritativo do envelope = tipo/status; NUNCA gate de string de bairro
  (canônico §9 conferencia-fontes: inclusão = R=1000m do centróide).
- Ambos degradam limpo: falha da macro nunca derruba o pipeline.
"""
from __future__ import annotations

import asyncio
import types

from google.adk.agents import BaseAgent

import agents.a3a_competitor_search as a3a
import agents.a3b_competitor_analysis as a3b


def _ctx(state: dict) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        session=types.SimpleNamespace(state=state), invocation_id="inv-a3"
    )


def _run(agent, ctx) -> list:
    async def _go():
        return [e async for e in agent._run_async_impl(ctx)]

    return asyncio.run(_go())


# ── Contrato estático: par determinístico sem LLM ─────────────────────────────

def test_a3a_e_baseagent_sem_llm():
    assert isinstance(a3a.competitor_search_agent, BaseAgent)
    assert getattr(a3a.competitor_search_agent, "model", None) is None
    assert a3a.competitor_search_agent.name == "CompetitorSearch"


def test_a3b_e_baseagent_sem_llm():
    assert isinstance(a3b.competitor_analysis_agent, BaseAgent)
    assert getattr(a3b.competitor_analysis_agent, "model", None) is None
    assert a3b.competitor_analysis_agent.name == "CompetitorAnalysis"
    # filtro é inline; não há callback pós-LLM
    assert getattr(a3b.competitor_analysis_agent, "after_agent_callback", None) is None


# ── A3a: grava concorrentes_brutos e degrada limpo ────────────────────────────

def test_a3a_grava_concorrentes_brutos(monkeypatch):
    captura: dict = {}

    async def _stub(tool_context, bairro, cidade):
        captura.update(bairro=bairro, cidade=cidade)
        return {"concorrentes_brutos": [{"nome": "Smart Fit"}], "redes_a0_cobertas": []}

    monkeypatch.setattr(a3a, "analisar_concorrentes_a3a_completo", _stub)
    evs = _run(
        a3a.competitor_search_agent,
        _ctx({"market_context": {"market_context": {"bairro": "Cocó", "cidade": "Fortaleza"}}}),
    )
    assert len(evs) == 1
    delta = evs[0].actions.state_delta
    assert list(delta) == ["concorrentes_brutos"]
    assert delta["concorrentes_brutos"]["concorrentes_brutos"] == [{"nome": "Smart Fit"}]
    assert captura == {"bairro": "Cocó", "cidade": "Fortaleza"}


def test_a3a_le_cidade_bairro_de_input_params(monkeypatch):
    """Deps-reverse: sem market_context, A3a ainda resolve loc via input_params."""
    captura: dict = {}

    async def _stub(tool_context, bairro, cidade):
        captura.update(bairro=bairro, cidade=cidade)
        return {"concorrentes_brutos": [], "redes_a0_cobertas": []}

    monkeypatch.setattr(a3a, "analisar_concorrentes_a3a_completo", _stub)
    _run(
        a3a.competitor_search_agent,
        _ctx({"input_params": {"bairro": "Centro", "cidade": "Pirapora"}}),
    )
    assert captura == {"bairro": "Centro", "cidade": "Pirapora"}


def test_a3a_macro_falha_degrada_com_lista_vazia(monkeypatch):
    async def _boom(tool_context, bairro, cidade):
        raise RuntimeError("places down")

    monkeypatch.setattr(a3a, "analisar_concorrentes_a3a_completo", _boom)
    evs = _run(a3a.competitor_search_agent, _ctx({"bairro": "X", "cidade": "Y"}))
    payload = evs[0].actions.state_delta["concorrentes_brutos"]
    assert payload["concorrentes_brutos"] == []
    assert "places down" in payload["erro"]


# ── A3b: grava inteligencia_competitiva + oferta e degrada limpo ──────────────

def test_a3b_grava_inteligencia_e_oferta(monkeypatch):
    envelope = {
        "inteligencia_competitiva": {
            "concorrentes_detalhados": [{"nome": "A", "endereco": "Rua X, Cocó", "tipos": ["gym"]}],
            "dores_dominantes": [{"dor": "lotação"}],
            "servicos_nao_oferecidos": ["natação"],
            "oportunidades_rankeadas": [{"titulo": "24h"}],
            "melhor_avaliada": {"nome": "A", "rating": 4.8},
        },
        "nivel_saturacao": "MEDIO",
        "score_concorrencia": 6.5,
    }
    monkeypatch.setattr(a3b, "analisar_concorrentes_completo", lambda shim: envelope)
    # oferta é best-effort — força vazio pra não bater na rede
    import tools.offer_mapper_tool as omt
    monkeypatch.setattr(omt, "mapear_oferta_competidores_completo", lambda shim: None)

    evs = _run(a3b.competitor_analysis_agent, _ctx({"input_params": {"tipo_negocio": "academia"}}))
    delta = evs[0].actions.state_delta
    assert set(delta) == {"inteligencia_competitiva", "oferta_concorrentes"}
    env = delta["inteligencia_competitiva"]
    assert env["posicionamento_recomendado"] and env["resumo_executivo"]
    assert "MEDIO" in env["resumo_executivo"]


def test_a3b_macro_falha_degrada_envelope_seguro(monkeypatch):
    def _boom(shim):
        raise RuntimeError("macro down")

    monkeypatch.setattr(a3b, "analisar_concorrentes_completo", _boom)
    import tools.offer_mapper_tool as omt
    monkeypatch.setattr(omt, "mapear_oferta_competidores_completo", lambda shim: None)

    evs = _run(a3b.competitor_analysis_agent, _ctx({}))
    env = evs[0].actions.state_delta["inteligencia_competitiva"]
    assert env["score_concorrencia"] == 7.0  # envelope de erro seguro
    assert env["inteligencia_competitiva"]["concorrentes_detalhados"] == []


# ── Invariante canônico §9: sem gate de string de bairro ──────────────────────

def test_a3b_filtro_nao_dropa_por_string_de_bairro():
    env = {"inteligencia_competitiva": {"concorrentes_detalhados": [
        {"nome": "Academia Cocó", "endereco": "Rua X, Cocó, Fortaleza", "tipos": ["gym"]},
        {"nome": "Smart Fit Aldeota", "endereco": "Av Y, Aldeota, Fortaleza", "tipos": ["gym"]},
    ]}}
    a3b._filtrar_envelope(env, {"bairro": "Cocó", "input_params": {"tipo_negocio": "academia"}})
    nomes = [c["nome"] for c in env["inteligencia_competitiva"]["concorrentes_detalhados"]]
    assert "Academia Cocó" in nomes and "Smart Fit Aldeota" in nomes
