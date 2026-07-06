"""Regressão do caso CT Greenlife (auditoria Gemini/4b211a02): a mineração de oferta
só via os detalhados do A3b (1–3) e os serviços do resto da praça viravam falso
'oportunidade de CRIAR'. Valida: expansão com brutos do A3a (fitness, dedupe, ordem),
o fluxo da macro com o lote mockado e o consumo do minerado pelo A9."""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tools.offer_mapper_tool as omt
from agents.a9_positioning_strategist import _gaps_reais, _servicos_minerados_state


def _brutos_coco():
    return [
        {"nome": "CT Greenlife", "tipos": ["gym"], "website": "https://greenlifeacademias.com.br", "num_avaliacoes": 64},
        {"nome": "Parque Estadual do Cocó", "tipos": ["park"], "website": "https://parque.ce.gov.br", "num_avaliacoes": 26383},
        {"nome": "Academia Smart Fit - Papicu", "tipos": ["gym"], "website": "https://smartfit.com.br", "num_avaliacoes": 1332},
        {"nome": "TBOX", "tipos": ["gym"], "num_avaliacoes": 16},
    ]


def test_expansao_filtra_dedupe_ordena():
    detalhados = [{"nome": "Academia Smart Fit - Papicu", "website": "https://smartfit.com.br"}]
    out = omt._expandir_com_brutos(detalhados, {"concorrentes_brutos": _brutos_coco()})
    nomes = [c["nome"] for c in out]
    assert nomes[0] == "Academia Smart Fit - Papicu"      # detalhado preservado na frente
    assert nomes.count("Academia Smart Fit - Papicu") == 1  # dedupe
    assert "Parque Estadual do Cocó" not in nomes          # não-fitness fora
    assert nomes.index("CT Greenlife") < nomes.index("TBOX")  # ordem por avaliações


def test_sem_brutos_nao_quebra():
    detalhados = [{"nome": "A", "website": "x"}]
    assert omt._expandir_com_brutos(detalhados, {}) == detalhados


def test_macro_minera_extras(monkeypatch):
    capturados = {}

    def _fake_lote(elegiveis):
        capturados["nomes"] = [c["nome"] for c in elegiveis]
        return [{"nome": c["nome"], "confiabilidade_fonte": 0.8,
                 "modalidades_keywords": ["crossfit"], "fonte_url_ok": True} for c in elegiveis]

    monkeypatch.setattr(omt, "_mapear_lote_async", _fake_lote)
    monkeypatch.setattr(omt, "_run_async_in_thread", lambda x: x)

    state = {
        "inteligencia_competitiva": {"concorrentes_detalhados": [
            {"nome": "Academia Smart Fit - Papicu", "website": "https://smartfit.com.br"}]},
        "concorrentes_brutos": _brutos_coco(),
    }
    ctx = types.SimpleNamespace(state=state)
    resultado = omt.mapear_oferta_competidores_completo(ctx)
    assert "CT Greenlife" in capturados["nomes"]
    assert "Parque Estadual do Cocó" not in capturados["nomes"]
    assert resultado["sucessos"] >= 2
    assert "CT Greenlife" in str(state.get("oferta_concorrentes"))


def test_a9_consome_minerado_do_state():
    state = {
        "inteligencia_competitiva": {"concorrentes_detalhados": [
            {"nome": "Academia Smart Fit", "planos_precos": [{"plano": "Fit", "inclui": ["Musculação"]}]}]},
        "oferta_concorrentes": {"oferta_concorrentes": {
            "ct-greenlife": {"nome": "CT Greenlife",
                             "modalidades": ["crossfit", "nutricao", "area_kids", "recovery"]},
        }},
    }
    assert _servicos_minerados_state(state) == {
        "Crossfit", "Nutrição integrada", "Aulas/espaço kids", "Recovery/fisioterapia"}
    gaps = _gaps_reais(state)
    assert "Crossfit" not in gaps
    assert "Nutrição integrada" not in gaps
    assert "Aulas/espaço kids" not in gaps
    assert "Musculação" not in gaps
    assert "Aulas de dança" in gaps
