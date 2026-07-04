"""Gate do Playwright de imóveis (LISTINGS_PLAYWRIGHT). Por default, o scraping
Playwright (OLX/ImovelWeb) fica FORA do caminho crítico — a cascata SearchAPI cobre
os imóveis. Evita o gargalo que estourava o pipeline (>30 min)."""
from __future__ import annotations

from unittest.mock import MagicMock

import tools.anchoring_tools as at


def _ctx(bairro="Vila Formosa"):
    ctx = MagicMock()
    ctx.state = {"input_params": {"bairro": bairro, "area_m2_min": 500, "area_m2_max": 1500}}
    return ctx


def _cascata_1_imovel(*a, **k):
    return [{"area_m2": 100, "url": "https://sp.olx.com.br/anuncio-1", "preco": 5000.0,
             "latitude": -23.55, "longitude": -46.63, "endereco": "Vila Formosa, SP"}]


def test_playwright_off_por_default(monkeypatch):
    """Sem LISTINGS_PLAYWRIGHT: NÃO chama o scraper Playwright; retorna a cascata."""
    monkeypatch.delenv("LISTINGS_PLAYWRIGHT", raising=False)
    monkeypatch.setattr("tools.listing_cascata.buscar_candidatos_cascata", _cascata_1_imovel)
    monkeypatch.setattr(at, "_anexar_aluguel_mrlr", lambda cands, c, b: cands)
    playwright = MagicMock()
    monkeypatch.setattr("tools.listing_tools.fetch_commercial_listings_async", playwright)

    res = at._fetch_listings_como_candidatos("São Paulo", "SP", _ctx(), -23.55, -46.63)

    playwright.assert_not_called()          # Playwright pulado
    assert len(res) >= 1                     # cascata SearchAPI retornada
    assert res[0].get("listing_url") == "https://sp.olx.com.br/anuncio-1"


def test_flag_liga_o_playwright(monkeypatch):
    """Com LISTINGS_PLAYWRIGHT=1, o caminho do scraper é alcançado (opt-in)."""
    monkeypatch.setenv("LISTINGS_PLAYWRIGHT", "1")
    monkeypatch.setattr("tools.listing_cascata.buscar_candidatos_cascata", _cascata_1_imovel)
    monkeypatch.setattr(at, "_anexar_aluguel_mrlr", lambda cands, c, b: cands)

    chamou = {"v": False}

    async def _fake_fetch(*a, **k):
        chamou["v"] = True
        return []  # scraper vazio → função cai no fallback da cascata

    monkeypatch.setattr("tools.listing_tools.fetch_commercial_listings_async", _fake_fetch)
    monkeypatch.setattr("tools.maps_tools.geocode_endereco", lambda *a, **k: None)

    at._fetch_listings_como_candidatos("São Paulo", "SP", _ctx(), -23.55, -46.63)
    assert chamou["v"] is True               # com a flag, o Playwright roda
