"""Recomendação de modelo com 2 gates complementares (renda-ponderado + físico):
premium inviável no realista vira recomendável em bairro top-renda SE fecha no teto de
captação (ACAD agressivo) E o pico simultâneo cabe na capacidade. Bairro pobre → barrado."""
from tools.financial_tools import (
    _escolher_cenario_recomendado,
    _fator_captacao,
    _viab_no_teto_captacao,
)


def _prem():
    return {
        "modelo": "Premium", "modelo_key": "premium", "viabilidade": "INVIAVEL",
        # estrutura REAL do cenário: matriculas[cal] = {"valor": int, ...} (não int cru)
        "matriculas": {"realista": {"valor": 690}, "agressivo": {"valor": 1035}},
        "receita_mensal": 201757.0, "ticket_realizado_estimado": 292.40,
        "custos_detalhados": {"outros": 6000.0}, "custos_fixos_total": 150000.0,
        "marketing_pct_faturamento": 0.12, "investimento_total": 1200000.0,
        "alunos_pico_calculado": 44, "capacidade_simultanea_pico": 287,
        "lucro_mensal_estimado": 20000.0, "payback_meses": 138,
    }


_MID = {"modelo": "Mid Market", "modelo_key": "mid", "viabilidade": "ALTO",
        "lucro_mensal_estimado": 80000.0, "payback_meses": 15}
_LOW = {"modelo": "Low Cost", "modelo_key": "low", "viabilidade": "ALTO",
        "lucro_mensal_estimado": 90000.0, "payback_meses": 12}


def test_fator_por_percentil():
    assert _fator_captacao(0.99) > 0.9        # top-renda empurra ao teto
    assert _fator_captacao(0.75) == 0.0       # no limiar, ainda realista
    assert _fator_captacao(0.4) == 0.0        # bairro comum
    assert _fator_captacao(None) == 0.0


def test_premium_viavel_no_teto_com_pico_folgado():
    t = _viab_no_teto_captacao(_prem(), 0.96)
    assert t is not None
    assert t["viabilidade"] != "INVIAVEL"     # fecha no teto
    assert t["pico_comporta"] is True         # 65 <= 287
    assert t["matriculas_alvo"] > 690


def test_bairro_rico_marca_premium_como_upside_nao_recomendacao():
    from tools.financial_tools import _faixa_key_de_modelo

    cen = {"low": dict(_LOW), "mid": dict(_MID), "premium": _prem()}
    melhor = _escolher_cenario_recomendado(cen, 4952.0, 0.99)
    # Teto-de-captação anota UPSIDE no premium, mas a recomendação NÃO é INVIAVEL
    # no realista (gate de viabilidade — auto-contradição no relatório).
    assert cen["premium"].get("_elegivel_teto") is True
    assert cen["premium"]["recomendado_no_teto_captacao"]["viabilidade"] != "INVIAVEL"
    assert melhor["modelo"] != "nenhum"
    assert _faixa_key_de_modelo(melhor.get("modelo") or "") != "premium"


def test_bairro_pobre_nao_eleva_premium():
    cen = {"low": dict(_LOW), "mid": dict(_MID), "premium": _prem()}
    melhor = _escolher_cenario_recomendado(cen, 1500.0, 0.20)
    assert melhor["modelo_key"] == "low"      # tier pobre + premium não elevado
    assert cen["premium"].get("_elegivel_teto") is None


def test_pico_estoura_nao_eleva():
    # capacidade física pequena → pico no teto estoura → não eleva mesmo rico
    prem = _prem()
    prem["capacidade_simultanea_pico"] = 50   # pico_alvo ~65 > 50
    cen = {"low": dict(_LOW), "mid": dict(_MID), "premium": prem}
    melhor = _escolher_cenario_recomendado(cen, 4952.0, 0.99)
    assert melhor["modelo_key"] != "premium"  # gate físico barrou
