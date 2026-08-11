"""Tests for prompt-only context slim-down (state integrity)."""
from __future__ import annotations

import json
from types import SimpleNamespace

from tools.context_slimmer import slim_market_context_for_prompt


def _sample_complete() -> dict:
    obras = []
    for i in range(12):
        obras.append(
            {
                "cno": f"90023011117{i}",
                "nome_obra": f"OBRA {i}",
                "area_m2": 1000 + i,
                "projecao_receita": {
                    "status": "ok",
                    "receita_mensal_estimada": {"realista": 900000 + i},
                },
                "capacidade_matriculas_estimada": 500,
            }
        )
    return {
        "cidade": "Fortaleza",
        "bairro": "Parangaba",
        "cruzamento_cno": {
            "obras_fitness_referencia": obras,
            "benchmark_tempo_obra_cno": {
                "obras_referencia": [{"cno": "1", "area_m2": 100}] * 8,
            },
            "cno_fitness_keyword_municipio": {
                "obras": [{"cno": "x"}, {"cno": "y"}],
            },
            "resumo_match": {"com_match": 3},
        },
        "fatos_parque_cnpj": {
            "composicao_parque": {"academia": {"count": 1223}},
            "metricas": {"parque_ativo_total": 1828},
            "novas_unidades_90d_por_segmento": {"academia": 10},
            "cruzamento_cno": {
                "obras_fitness_referencia": obras[:3],
            },
        },
        "zoneamento": {"mapa_svg": "<svg>" + ("M" * 5000) + "</svg>", "zona": "ZEDUS"},
        "fluxo_pedestre": {"leitura": "texto longo " * 200, "score": 80},
        "demanda_futura": {
            "total": 2,
            "obras": [{"nome": "A", "ocupacao_fonte": {"detalhe": "pesado"}}],
        },
        "obras_cno_em_curso": {
            "obras": [
                {
                    "nome": "Em curso",
                    "projecao_receita": {"x": 1},
                    "area_m2": 900,
                }
            ],
            "benchmark_tempo_obra": {"obras_referencia": [1, 2, 3]},
        },
    }


def test_state_mantem_dados_completos():
    completo = _sample_complete()
    slim = slim_market_context_for_prompt(completo)

    assert len(completo["cruzamento_cno"]["obras_fitness_referencia"]) == 12
    assert (
        completo["cruzamento_cno"]["obras_fitness_referencia"][0]["projecao_receita"]
        is not None
    )
    assert completo["fatos_parque_cnpj"]["composicao_parque"]["academia"]["count"] == 1223
    assert "<svg>" in completo["zoneamento"]["mapa_svg"]
    assert "leitura" in completo["fluxo_pedestre"]

    assert slim["cruzamento_cno"]["obras_fitness_referencia"] == "[removido: 12 itens]"
    assert isinstance(slim["fatos_parque_cnpj"]["composicao_parque"], str)
    assert slim["fatos_parque_cnpj"]["composicao_parque"].startswith("[removido:")
    assert slim["zoneamento"]["mapa_svg"] == "[removido]"
    assert "leitura" not in slim["fluxo_pedestre"]
    assert slim["cruzamento_cno"]["resumo_match"]["com_match"] == 3


def test_prompt_e_slim_reducao():
    completo = _sample_complete()
    slim = slim_market_context_for_prompt(completo)
    tamanho_completo = len(json.dumps(completo, ensure_ascii=False)) // 4
    tamanho_slim = len(json.dumps(slim, ensure_ascii=False)) // 4
    assert tamanho_slim < tamanho_completo * 0.5
    assert tamanho_slim < tamanho_completo


def test_downstream_le_state_completo():
    """A4/A6 leem state — slim não pode alterar a referência do state."""
    state = {"market_context": _sample_complete()}
    _ = slim_market_context_for_prompt(state["market_context"])
    mc = state["market_context"]
    assert len(mc["cruzamento_cno"]["obras_fitness_referencia"]) == 12
    assert mc["cruzamento_cno"]["obras_fitness_referencia"][0]["projecao_receita"] is not None


def test_a0_after_tool_persists_full_returns_slim():
    from agents.a0_context_builder import _a0_after_tool_slim

    full = _sample_complete()
    full["status"] = "ok"
    st: dict = {}
    tool = SimpleNamespace(name="dados_parque_cnpj_para_a0")
    ctx = SimpleNamespace(state=st)
    slim = _a0_after_tool_slim(tool, {}, ctx, full)

    assert isinstance(slim, dict)
    assert slim.get("_slim_for_prompt") is True
    assert slim["cruzamento_cno"]["obras_fitness_referencia"] == "[removido: 12 itens]"
    snap = st["a0_tool_snapshots"]["dados_parque_cnpj_para_a0"]
    assert len(snap["cruzamento_cno"]["obras_fitness_referencia"]) == 12
    assert len(full["cruzamento_cno"]["obras_fitness_referencia"]) == 12


def test_a0_loop_cap_failsoft():
    from agents.a0_context_builder import MAX_A0_LLM_CALLS, _a0_before_model_callback

    st = {
        "_a0_llm_calls": MAX_A0_LLM_CALLS,
        "input_params": {"cidade": "Fortaleza", "bairro": "Parangaba", "uf": "CE"},
    }
    ctx = SimpleNamespace(state=st)
    resp = _a0_before_model_callback(ctx, llm_request=None)
    assert resp is not None
    assert st.get("a0_degraded") is True
    content = resp.content
    assert content is not None and content.parts
    text = content.parts[0].text
    assert isinstance(text, str)
    payload = json.loads(text)
    assert payload["market_context"]["a0_degraded"] is True


def test_a0_agent_callbacks_wired():
    from agents.a0_context_builder import (
        _a0_after_tool_slim,
        _a0_before_model_callback,
        _a0_on_model_error_callback,
        context_builder_agent,
    )

    assert getattr(context_builder_agent, "after_tool_callback", None) is _a0_after_tool_slim
    assert getattr(context_builder_agent, "before_model_callback", None) is _a0_before_model_callback
    assert getattr(context_builder_agent, "on_model_error_callback", None) is _a0_on_model_error_callback
