"""A9 ERRC data-tied: gaps computados do dado REAL de oferta (planos_precos.inclui),
não do exemplo viciado do prompt. Recovery deixa de ser falso-gap quando um
concorrente o oferece."""
from agents.a9_positioning_strategist import _resumo_oferta_e_gaps, _servicos_do_concorrente


def _state(concs):
    return {"inteligencia_competitiva": {"concorrentes_detalhados": concs}}


def test_servicos_do_concorrente_do_inclui_e_nome():
    # SmartFit Black inclui "Cadeira de massagem" -> Recovery; nome com natação -> Natação
    c = {"nome": "Smart Fit", "planos_precos": [{"plano": "Black", "inclui": ["Área de musculação", "Cadeira de massagem"]}]}
    svc = _servicos_do_concorrente(c)
    assert "Musculação" in svc
    assert "Recovery/fisioterapia" in svc  # massagem -> recovery


def test_recovery_nao_e_gap_quando_concorrente_oferece():
    state = _state([
        {"nome": "Smart Fit", "planos_precos": [{"plano": "Black", "inclui": ["Cadeira de massagem", "musculação"]}]},
        {"nome": "REK CrossFit", "planos_precos": [{"plano": "Crossfit", "inclui": ["3x semana"]}]},
    ])
    txt = _resumo_oferta_e_gaps(state)
    # Recovery foi detectado -> NÃO aparece na linha de GAPS REAIS
    gaps_line = [l for l in txt.splitlines() if l.startswith("GAPS REAIS")][0]
    assert "Recovery" not in gaps_line


def test_nutricao_e_gap_quando_ninguem_oferece():
    state = _state([
        {"nome": "REK CrossFit", "planos_precos": [{"plano": "Crossfit", "inclui": ["3x semana"]}]},
        {"nome": "VS Club Musculação natação", "planos_precos": []},
    ])
    txt = _resumo_oferta_e_gaps(state)
    gaps_line = [l for l in txt.splitlines() if l.startswith("GAPS REAIS")][0]
    assert "Nutrição integrada" in gaps_line  # ninguém oferece -> gap real


def test_sem_concorrentes_retorna_none():
    assert _resumo_oferta_e_gaps(_state([])) is None
    assert _resumo_oferta_e_gaps({"inteligencia_competitiva": {}}) is None
