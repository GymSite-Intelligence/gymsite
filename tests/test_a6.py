"""A6 ReportConsolidator — VERIFIER GATE (Steinberger loop).

BENCHMARK FIXO: não altere este arquivo para “fazer passar”.
Só edite `agents/a6_report_consolidator.py` até:

  python -m pytest tests/test_a6.py -q --tb=short -x

sair com código 0 (7 passed).

Contrato: A6 usa LLM somente para narrativa. Dados financeiros, competitivos,
Top 3, scores e persistência são protegidos por cálculo e alinhamento
determinísticos. Nenhum número novo pode nascer da narrativa.
"""
from __future__ import annotations

import types

from google.adk.agents import Agent

import agents.a6_report_consolidator as a6


def _tool_names(agent) -> set[str]:
    names: set[str] = set()
    for tool in getattr(agent, "tools", None) or []:
        name = getattr(tool, "__name__", None) or getattr(tool, "name", None)
        if not name:
            function = getattr(tool, "func", None)
            name = getattr(function, "__name__", None)
        if name:
            names.add(str(name))
    return names


def test_a6_contrato_do_agente_e_callbacks():
    agent = a6.report_consolidator_agent
    assert isinstance(agent, Agent)
    assert agent.name == "ReportConsolidator"
    assert getattr(agent, "output_key", None) == "relatorio_md"
    assert getattr(agent, "before_model_callback", None) is a6._a6_before_model_callback
    assert getattr(agent, "before_agent_callback", None) is a6._a6_precompute_callback
    assert getattr(agent, "after_agent_callback", None) is a6._a6_after_agent_callback


def test_a6_tools_nao_coletam_numeros_novos():
    # tools=[]: data/bairros injetados no before_model/before_agent.
    # Evita alucinação de tool de outro agente (derrubava Sequential).
    assert _tool_names(a6.report_consolidator_agent) == set()


def test_a6_snapshot_financeiro_vence_narrativa_incompleta():
    snapshot = {
        "aluguel_mensal": 10_000.0,
        "score_viabilidade": 7.5,
        "cenarios": {"mid": {"payback_meses": 18}},
    }
    state = {
        "analise_financeira_pronto": snapshot,
        "analise_financeira": {
            "analise_financeira": {"justificativa": "Texto determinístico do A4"}
        },
    }
    result = a6._resolver_analise_financeira(state)
    assert result["aluguel_mensal"] == 10_000.0
    assert result["score_viabilidade"] == 7.5
    assert result["justificativa"] == "Texto determinístico do A4"


def test_a6_top3_renderiza_ranking_mrlr_e_payback():
    markdown = a6._renderizar_md_top3_candidatos(
        [
            {
                "nome": "Galpão Centro",
                "endereco": "Centro, Pirapora - MG",
                "area_m2": 800,
                "score_geoscout": 7,
                "score_geo_norm": 0.7,
                "score_payback_norm": 0.8,
                "score_composto": 0.765,
                "carimbo_aluguel": "R$ 10.000,00 · 800 m² · MRLR · R$ 12,50/m²",
                "payback_est_meses": 18.2,
                "qualidade_sinal": "direto-listing-bairro",
            }
        ]
    )
    assert "35% geo / 65% payback" in markdown
    assert "R$ 10.000,00" in markdown and "MRLR" in markdown
    assert "18.2 meses" in markdown
    assert "direto-listing-bairro" in markdown
    assert "preço do anúncio" not in markdown.lower()


def test_a6_top3_vazio_e_honesto():
    markdown = a6._renderizar_md_top3_candidatos([])
    assert "Não há candidatos a imóveis" in markdown


def test_a6_alinhador_substitui_top3_inventado_pelo_estruturado():
    markdown = (
        "## 🏆 Top 3 Candidatos\n\n"
        "### #1 — Imóvel inventado — Score Geral 10\n\n"
        "## 🏗️ Checklist de Diligência do Imóvel\n\nValidar documentação.\n"
    )
    structured = {
        "top_3_candidatos": [
            {
                "nome": "Galpão Real",
                "endereco": "Centro, Pirapora - MG",
                "score_geoscout": 7,
                "qualidade_sinal": "direto-listing-bairro",
            }
        ]
    }
    aligned = a6._alinhar_markdown_ao_estruturado(markdown, structured)
    assert "Galpão Real" in aligned
    assert "Imóvel inventado" not in aligned


def test_a6_precompute_injeta_blocos_deterministicos(monkeypatch):
    monkeypatch.setattr(
        a6,
        "bairros_alternativos_inteligentes",
        lambda context: {"bairros_alternativos": [{"bairro": "Centro"}]},
    )
    monkeypatch.setattr(
        a6,
        "_precompute_entrantes_cnpj",
        lambda context: {"status": "ok", "entrantes": []},
    )
    monkeypatch.setattr(
        a6,
        "_precompute_obras_cno",
        lambda context: {"status": "ok", "obras": []},
    )
    monkeypatch.setattr(a6, "_telemetry_before", lambda context: None)
    context = types.SimpleNamespace(state={})

    a6._a6_precompute_callback(context)

    assert context.state["bairros_alternativos_pronto"]["bairros_alternativos"]
    assert context.state["entrantes_cnpj_pronto"]["status"] == "ok"
    assert context.state["obras_cno_pronto"]["status"] == "ok"
