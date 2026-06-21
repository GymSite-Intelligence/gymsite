"""A4 escolhe o tier do modelo pela renda 2022 (IBGE), não pelo CKAN 2010 (bug Cocó)."""
import tools.financial_tools as ft
import tools.posicionamento_renda as pr


def test_tier_thresholds():
    assert ft._tier_mercado_por_renda(None) == "mid"
    assert ft._tier_mercado_por_renda(0) == "mid"
    assert ft._tier_mercado_por_renda(1800) == "low"
    assert ft._tier_mercado_por_renda(3000) == "mid"
    assert ft._tier_mercado_por_renda(4952) == "premium"


def test_renda_prefere_fonte_2022(monkeypatch):
    # IBGE 2022 (renda_pc) é primário — Cocó top-1% deve dar premium, não low.
    monkeypatch.setattr(pr, "renda_bairro_ipece", lambda c, u, b: {"renda_pc": 4952.75})
    # _renda_media_bairro agora retorna (valor, fonte) — fonte alimenta viabilidade.renda_fonte
    v, fonte = ft._renda_media_bairro("Fortaleza", "Cocó", "CE")
    assert v == 4952.75
    assert "2022" in fonte
    assert ft._tier_mercado_por_renda(v) == "premium"


def test_fallback_quando_2022_ausente(monkeypatch):
    # Sem cobertura 2022 → cai no CKAN (per capita), sem crash.
    monkeypatch.setattr(pr, "renda_bairro_ipece", lambda c, u, b: None)
    monkeypatch.setattr(
        ft, "_renda_media_bairro", ft._renda_media_bairro
    )  # garante uso da versão real
    import tools.bairro_renda_loader as brl
    monkeypatch.setattr(
        brl, "enrich_demografia_bairro",
        lambda base, c, b, u: {"bairro": {"renda_media_per_capita": 1800.0}},
    )
    v, fonte = ft._renda_media_bairro("X", "Y", "CE")
    assert v == 1800.0
    assert "CKAN" in fonte
    assert ft._tier_mercado_por_renda(v) == "low"
