"""Override determinístico dos números CNPJ no A0 (close do último 'LLM produz dado').

A0 é LlmAgent (Deep Research qualitativo), mas o LLM não pode produzir número. O
after_agent_callback `_a0_override_cnpj_numeros` re-roda a tool determinística e
sobrescreve os campos numéricos do CNPJ + pluga arvore_2x2_parque. Qualitativo fica.
Offline: mocka dados_parque_cnpj_para_a0 (sem rede/DB).
"""
import types as _t

import agents.a0_context_builder as a0

_FAKE_TOOL = {
    "status": "ok",
    "arvore_2x2_parque": {"estoque_municipio": 1158, "estoque_bairro": 38,
                          "entrantes_municipio_90d": 41, "entrantes_bairro_90d": 0},
    "metricas_objetivas": {
        "parque_ativo_total": 1828, "parque_comercial_total": 1158,
        "novos_cnpj_fitness_90d": 41, "excluidos_saude_clinica": 95,
        "pendentes_validacao": 0, "composicao_parque": {"academia": {"count": 900}},
        "novas_unidades_90d_por_segmento": {}, "serie_aberturas_anual": {},
    },
    "indicadores_derivados": {"taxa_renovacao_parque_90d_pct": 3.5},
    "cruzamento_cno": {}, "lacunas_conhecidas": [],
}


def _ctx(state):
    return _t.SimpleNamespace(state=state)


def _mc_llm(extra=None):
    inner = {"cidade": "Fortaleza", "uf": "CE", "bairro": "Cocó",
             "ticket_medio_mercado": "R$ 120", "aluguel_medio_m2": "R$ 60",
             "tendencia_mercado": "crescimento", "insights_estrategicos": ["fato (DR)"],
             "parque_ativo_total": 9999, "parque_comercial_total": 8888,
             "novos_cnpj_fitness_90d": 777}
    inner.update(extra or {})
    return {"input_params": {"cidade": "Fortaleza", "uf": "CE", "bairro": "Cocó"},
            "market_context": {"market_context": inner}}


def test_sobrescreve_numero_do_llm(monkeypatch):
    monkeypatch.setattr("tools.cnpj_fitness_tools.dados_parque_cnpj_para_a0",
                        lambda *a, **k: _FAKE_TOOL)
    st = _mc_llm()
    a0._a0_override_cnpj_numeros(_ctx(st))
    inner = st["market_context"]["market_context"]
    assert inner["parque_ativo_total"] == 1828       # era 9999
    assert inner["parque_comercial_total"] == 1158   # era 8888
    assert inner["novos_cnpj_fitness_90d"] == 41      # era 777
    assert inner["academias_ativas_cidade_cnpj"] == 1828
    assert inner["_cnpj_override"] == "deterministico_tool"


def test_pluga_arvore_2x2(monkeypatch):
    monkeypatch.setattr("tools.cnpj_fitness_tools.dados_parque_cnpj_para_a0",
                        lambda *a, **k: _FAKE_TOOL)
    st = _mc_llm()
    a0._a0_override_cnpj_numeros(_ctx(st))
    arv = st["market_context"]["market_context"]["arvore_2x2_parque"]
    assert arv["estoque_municipio"] == 1158 and arv["estoque_bairro"] == 38


def test_qualitativo_preservado(monkeypatch):
    monkeypatch.setattr("tools.cnpj_fitness_tools.dados_parque_cnpj_para_a0",
                        lambda *a, **k: _FAKE_TOOL)
    st = _mc_llm()
    a0._a0_override_cnpj_numeros(_ctx(st))
    inner = st["market_context"]["market_context"]
    assert inner["ticket_medio_mercado"] == "R$ 120"   # LLM/DR fica
    assert inner["aluguel_medio_m2"] == "R$ 60"
    assert inner["tendencia_mercado"] == "crescimento"
    assert inner["insights_estrategicos"] == ["fato (DR)"]


def test_tool_falha_nao_altera(monkeypatch):
    monkeypatch.setattr("tools.cnpj_fitness_tools.dados_parque_cnpj_para_a0",
                        lambda *a, **k: {"status": "erro"})
    st = _mc_llm()
    a0._a0_override_cnpj_numeros(_ctx(st))
    # tool falhou → não sobrescreve (mantém o do LLM, não inventa)
    assert st["market_context"]["market_context"]["parque_ativo_total"] == 9999


def test_sem_cidade_nem_chama_tool(monkeypatch):
    chamou = {"v": False}

    def _f(*a, **k):
        chamou["v"] = True
        return {"status": "ok"}

    monkeypatch.setattr("tools.cnpj_fitness_tools.dados_parque_cnpj_para_a0", _f)
    st = {"market_context": {"market_context": {}}}  # sem cidade
    a0._a0_override_cnpj_numeros(_ctx(st))
    assert chamou["v"] is False
