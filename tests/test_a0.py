"""A0 ContextBuilder — VERIFIER GATE (Steinberger loop).

BENCHMARK FIXO: não altere este arquivo para “fazer passar”.
Só edite `agents/a0_context_builder.py` até:

  pytest tests/test_a0.py

sair com código 0 (4 passed).
"""
from __future__ import annotations

import types as _t

import agents.a0_context_builder as a0

_FORBIDDEN_TOOLS = frozenset(
    {
        "rodar_deep_research",
        "rodar_kimi_research",
        "google_search",
        "buscar_conhecimento",
    }
)


def _tool_names(agent) -> set[str]:
    names: set[str] = set()
    for t in getattr(agent, "tools", None) or []:
        name = getattr(t, "__name__", None) or getattr(t, "name", None)
        if not name:
            fn = getattr(t, "func", None)
            name = getattr(fn, "__name__", None) if fn is not None else None
        names.add(str(name or t))
    return names


def test_a0_tools_bundle_only():
    """CONTRATO BUNDLE-ONLY: sem DR/Kimi/search/Discovery nas tools."""
    names = _tool_names(a0.context_builder_agent)
    assert "carregar_market_bundle" in names
    assert "dados_parque_cnpj_para_a0" in names
    assert "fatos_competicao_local" in names
    assert names.isdisjoint(_FORBIDDEN_TOOLS), (
        f"tools proibidas no A0: {names & _FORBIDDEN_TOOLS}"
    )


def test_a0_after_agent_callback_is_cnpj_override():
    cb = getattr(a0.context_builder_agent, "after_agent_callback", None)
    assert cb is a0._a0_override_cnpj_numeros


def test_a0_output_key_market_context():
    assert getattr(a0.context_builder_agent, "output_key", None) == "market_context"


def test_a0_override_passa_bairro_e_dias_90(monkeypatch):
    seen: dict = {}

    def _fake(cidade, uf="", dias=90, bairro="", **_kw):
        seen["cidade"] = cidade
        seen["uf"] = uf
        seen["dias"] = dias
        seen["bairro"] = bairro
        return {
            "status": "ok",
            "arvore_2x2_parque": {},
            "metricas_objetivas": {
                "parque_ativo_total": 10,
                "parque_comercial_total": 8,
                "novos_cnpj_fitness_90d": 1,
                "excluidos_saude_clinica": 0,
                "pendentes_validacao": 0,
                "composicao_parque": {},
                "novas_unidades_90d_por_segmento": {},
                "serie_aberturas_anual": {},
            },
            "indicadores_derivados": {},
            "cruzamento_cno": {},
            "lacunas_conhecidas": [],
        }

    monkeypatch.setattr("tools.cnpj_fitness_tools.dados_parque_cnpj_para_a0", _fake)
    st = {
        "input_params": {"cidade": "Fortaleza", "uf": "CE", "bairro": "Cocó"},
        "market_context": {
            "market_context": {
                "cidade": "Fortaleza",
                "uf": "CE",
                "bairro": "Cocó",
                "parque_ativo_total": 0,
            }
        },
    }
    a0._a0_override_cnpj_numeros(_t.SimpleNamespace(state=st))
    assert seen["cidade"] == "Fortaleza"
    assert seen["uf"] == "CE"
    assert seen["bairro"] == "Cocó"
    assert seen["dias"] == 90
