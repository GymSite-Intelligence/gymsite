"""PONTO 99 — sanitização anual/mensal de planos L3.6."""

from tools.instagram_highlights_gemini import (
    _extrair_precos_do_markdown,
    _sanitizar_plano,
    elevar_confianca,
)


def test_anual_nome_converte_mesmo_abaixo_de_800():
    p = _sanitizar_plano(
        {"plano": "Plano Anual - Black Friday", "preco_brl": 500.0},
        "Plano Anual - Black Friday: R$ 500,00",
    )
    assert p["periodo"] == "anual"
    assert p["preco_mensal_brl"] == round(500 / 12, 2)
    assert "÷12" in (p.get("observacao") or "")


def test_mensal_normal():
    p = _sanitizar_plano(
        {"plano": "Plano Acessível", "preco_brl": 49.0},
        "Plano Acessível: R$ 49,00",
    )
    assert p["periodo"] == "mensal"
    assert p["preco_mensal_brl"] == 49.0
    assert not p.get("suspeito")


def test_preco_suspeito_baixo():
    p = _sanitizar_plano(
        {"plano": "Promo", "preco_brl": 5.0},
        "Promo: R$ 5,00",
    )
    assert p.get("suspeito") is True
    assert p["periodo"] == "indeterminado"


def test_extrair_markdown_athletic_like():
    md = (
        "- Plano Acessível: R$ 49,00\n"
        "- Plano Anual - Black Friday: R$ 500,00\n"
    )
    planos = _extrair_precos_do_markdown(md)
    assert len(planos) >= 2
    by_name = {p["plano"].lower(): p for p in planos}
    acessivel = next(p for p in planos if "acess" in p["plano"].lower())
    anual = next(p for p in planos if "anual" in p["plano"].lower())
    assert acessivel["preco_mensal_brl"] == 49.0
    assert acessivel["periodo"] == "mensal"
    assert anual["periodo"] == "anual"
    assert anual["preco_mensal_brl"] == round(500 / 12, 2)


def test_elevar_confianca():
    assert elevar_confianca("baixa", "media") == "media"
    assert elevar_confianca("media", "alta") == "alta"
    assert elevar_confianca("alta", "baixa") == "alta"
