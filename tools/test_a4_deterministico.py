"""A4 FinancialEstimator determinizado (BaseAgent, sem LLM)."""
from agents.a4_financial_estimator import (
    FinancialEstimatorAgent, financial_estimator_agent,
    _derivar_area, _justificativa_det, _top1_latlng,
)


def test_a4_baseagent_sem_llm():
    from google.adk.agents import BaseAgent
    assert isinstance(financial_estimator_agent, BaseAgent)
    assert isinstance(financial_estimator_agent, FinancialEstimatorAgent)
    assert getattr(financial_estimator_agent, "model", None) is None


def test_area_da_media():
    assert _derivar_area({"area_m2_min": 800, "area_m2_max": 1500}, "academia") == 1150.0


def test_area_default_por_tipo():
    assert _derivar_area({}, "studio_pilates") == 215.0
    assert _derivar_area({}, "academia") == 1150.0


def test_justificativa_template():
    r = {"recomendacao_modelo": "Mid Market",
         "cenarios": {"m": {"modelo": "Mid Market", "margem_percentual": 39, "payback_meses": 17}}}
    j = _justificativa_det(r, "Cocó", "predominantemente_feminino")
    assert "Mid Market" in j and "39%" in j and "17m" in j
    assert "Pilates" in j  # nota de gênero


def test_justificativa_misto_sem_nota():
    r = {"recomendacao_modelo": "Low Cost", "cenarios": {}}
    j = _justificativa_det(r, "X", "misto")
    assert "Low Cost" in j


def test_top1_latlng():
    st = {"candidatos_geoscout_pronto": {"candidatos": [{"lat": -3.7, "lng": -38.5}]}}
    assert _top1_latlng(st) == (-3.7, -38.5)
    assert _top1_latlng({}) == (None, None)
