"""Mineração de oferta dos concorrentes (planos + serviços) — substrato da ERRC.

Bugs corrigidos: (1) nutrição/recovery não eram detectados -> viravam falso-gap
eterno na ERRC; (2) período do plano (mensal/anual) não era capturado quando vinha
ANTES do valor ('Mensal R$ 159').
"""
from tools.competitor_offer_mapper import _detectar_modalidades, _detectar_precos, _norm_periodo


def test_detecta_nutricao_e_recovery():
    # Os 2 serviços que a ERRC sempre manda "Criar" — DEVEM ser detectados quando
    # o concorrente os oferece, senão viram falso-gap.
    txt = "Oferecemos Nutrição esportiva, acompanhamento nutricional, Recovery, fisioterapia e massagem."
    mod = _detectar_modalidades(txt)
    assert "nutricao" in mod
    assert "recovery" in mod


def test_detecta_modalidades_comuns():
    mod = _detectar_modalidades("Musculação, Crossfit, Yoga, Pilates, Natação, Spinning")
    for m in ("musculacao", "crossfit", "yoga", "pilates", "piscina", "spinning"):
        assert m in mod


def test_preco_periodo_antes_e_depois():
    prec = _detectar_precos(
        "Mensal R$ 159,90 | Trimestral R$ 429,00 | Plano anual: R$ 1.499,00 | R$ 89,90/mês"
    )
    by = {(p["valor_brl"], p["periodo"]) for p in prec}
    assert (159.9, "mensal") in by      # período ANTES do valor
    assert (429.0, "trimestral") in by
    assert (1499.0, "anual") in by      # 'Plano anual: R$'
    assert (89.9, "mensal") in by       # período DEPOIS (/mês)


def test_norm_periodo():
    assert _norm_periodo("Mensal") == "mensal"
    assert _norm_periodo("por mês") == "mensal"
    assert _norm_periodo("anual") == "anual"
    assert _norm_periodo("por ano") == "anual"
    assert _norm_periodo("trimestre") == "trimestral"
    assert _norm_periodo(None) == "indefinido"


def test_preco_fora_de_faixa_ignorado():
    # Valores absurdos (< 10 ou > 5000) não são planos.
    prec = _detectar_precos("R$ 5,00 estacionamento | R$ 50.000,00 patrimônio")
    assert prec == []
