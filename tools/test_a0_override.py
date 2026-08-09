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
    "arvore_oferta": {
        "estoque_municipio": 1158,
        "baixas_municipio_90d": 12,
        "baixas_municipio_q": 8,
        "entrantes_municipio_q": 30,
        "saldo_oferta_municipio_q": 22,
        "pressao_oferta_municipio_q": "expansao",
        "janela_q": {"label": "2026-Q1"},
        "as_of": "2026-05-31",
    },
    "redes": {
        "ativos_multiunidade_municipio": 40,
        "ativos_solo_municipio": 1118,
        "criterio": "cnpj_basico com >=2 estab. ativos fitness no BR",
    },
    "metricas_objetivas": {
        "parque_ativo_total": 1828, "parque_comercial_total": 1158,
        "novos_cnpj_fitness_90d": 41, "excluidos_saude_clinica": 95,
        "pendentes_validacao": 0, "composicao_parque": {"academia": {"count": 900}},
        "novas_unidades_90d_por_segmento": {}, "serie_aberturas_anual": {},
        "baixas_cnpj_fitness_90d": 12,
        "baixas_cnpj_fitness_q": 8,
        "entrantes_cnpj_fitness_q": 30,
        "saldo_oferta_q": 22,
        "pressao_oferta_q": "expansao",
        "janela_q_label": "2026-Q1",
        "as_of": "2026-05-31",
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


def test_pluga_arvore_oferta_e_redes(monkeypatch):
    monkeypatch.setattr("tools.cnpj_fitness_tools.dados_parque_cnpj_para_a0",
                        lambda *a, **k: _FAKE_TOOL)
    st = _mc_llm()
    a0._a0_override_cnpj_numeros(_ctx(st))
    inner = st["market_context"]["market_context"]
    assert inner["arvore_oferta"]["baixas_municipio_90d"] == 12
    assert inner["redes"]["ativos_multiunidade_municipio"] == 40
    assert inner["baixas_cnpj_fitness_90d"] == 12
    assert inner["pressao_oferta_q"] == "expansao"
    assert inner["janela_q_label"] == "2026-Q1"
    assert inner["cnpj_as_of"] == "2026-05-31"


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


# ── Saneamento do esqueleto do schema (bug Pirapora) ────────────────────────
# Sem market_bundle, o LLM às vezes ecoa os literais de REFERÊNCIA do prompt
# ("crescimento|estavel|retracao", "fato+fonte N", "YYYY-MM-DD") como se fossem
# dado. Vazou pro PDF do cliente. O override determinístico troca por
# "dados_nao_disponiveis" (contrato do próprio prompt, §DEGRADAÇÃO).


def test_saneia_tendencia_esqueleto(monkeypatch):
    monkeypatch.setattr("tools.cnpj_fitness_tools.dados_parque_cnpj_para_a0",
                        lambda *a, **k: _FAKE_TOOL)
    st = _mc_llm({"tendencia_mercado": "crescimento|estavel|retracao"})
    a0._a0_override_cnpj_numeros(_ctx(st))
    assert st["market_context"]["market_context"]["tendencia_mercado"] == "dados_nao_disponiveis"


def test_saneia_insights_esqueleto(monkeypatch):
    monkeypatch.setattr("tools.cnpj_fitness_tools.dados_parque_cnpj_para_a0",
                        lambda *a, **k: _FAKE_TOOL)
    st = _mc_llm({"insights_estrategicos": ["fato+fonte 1", "fato+fonte 2", "fato+fonte 3"]})
    a0._a0_override_cnpj_numeros(_ctx(st))
    assert st["market_context"]["market_context"]["insights_estrategicos"] == []


def test_saneia_data_coleta_placeholder(monkeypatch):
    monkeypatch.setattr("tools.cnpj_fitness_tools.dados_parque_cnpj_para_a0",
                        lambda *a, **k: _FAKE_TOOL)
    st = _mc_llm({"data_coleta": "YYYY-MM-DD"})
    a0._a0_override_cnpj_numeros(_ctx(st))
    assert st["market_context"]["market_context"]["data_coleta"] == ""


def test_nao_toca_tendencia_real(monkeypatch):
    monkeypatch.setattr("tools.cnpj_fitness_tools.dados_parque_cnpj_para_a0",
                        lambda *a, **k: _FAKE_TOOL)
    st = _mc_llm({"tendencia_mercado": "estavel",
                  "insights_estrategicos": ["Parque 46 CNPJ ativos (CNPJ)"]})
    a0._a0_override_cnpj_numeros(_ctx(st))
    inner = st["market_context"]["market_context"]
    assert inner["tendencia_mercado"] == "estavel"
    assert inner["insights_estrategicos"] == ["Parque 46 CNPJ ativos (CNPJ)"]


def test_saneia_mesmo_com_cnpj_tool_falhando(monkeypatch):
    """Guardrail roda independente do CNPJ — é o caminho exato do Pirapora."""
    monkeypatch.setattr("tools.cnpj_fitness_tools.dados_parque_cnpj_para_a0",
                        lambda *a, **k: {"status": "erro"})
    st = _mc_llm({"tendencia_mercado": "crescimento|estavel|retracao"})
    a0._a0_override_cnpj_numeros(_ctx(st))
    inner = st["market_context"]["market_context"]
    assert inner["tendencia_mercado"] == "dados_nao_disponiveis"  # saneado
    assert inner["parque_ativo_total"] == 9999  # número NÃO tocado (tool falhou)
