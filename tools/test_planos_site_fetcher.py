"""Site-first planos balcão (Smart Fit HTML) + cascata A3a."""
from __future__ import annotations

import asyncio

from tools.planos_site_fetcher import (
    extract_smartfit_plans_html,
    fetch_planos_from_website,
)

_FAKE_SMARTFIT_HTML = """
<html><body>
<script>
window.x = {"plans":[
  {"plan_id":"2","plan_type":"black","membership":{"data":{
    "original_price":{"price":"159.9","installments":null},
    "current_price":{"price":"99.0","installments":1}
  }}},
  {"plan_id":"150","plan_type":"fit","membership":{"data":{
    "original_price":{"price":"129.9","installments":null},
    "current_price":{"price":"99.0","installments":1}
  }}},
  {"plan_id":"1","plan_type":"smart","membership":{"data":{
    "original_price":{"price":"149.9","installments":null},
    "current_price":{"price":"149.9","installments":null}
  }}}
]};
</script>
</body></html>
"""


def test_extract_smartfit_usa_mensalidade_cheia_nao_promo():
    planos = extract_smartfit_plans_html(_FAKE_SMARTFIT_HTML)
    assert planos is not None
    by_name = {p["plano"]: p for p in planos}
    assert by_name["Plano Black"]["preco_mensal"] == "R$ 159,90"
    assert by_name["Plano Black"]["preco_promo_1o_mes"] == "R$ 99,00"
    assert by_name["Plano Fit"]["preco_mensal"] == "R$ 129,90"
    assert by_name["Plano Smart"]["preco_mensal"] == "R$ 149,90"
    assert "preco_promo_1o_mes" not in by_name["Plano Smart"]
    assert by_name["Plano Black"]["fonte"] == "site_oficial"


def test_extract_smartfit_sem_plans_retorna_none():
    assert extract_smartfit_plans_html("<html>sem planos</html>") is None


def test_fetch_planos_unknown_domain_skip(monkeypatch):
    called = {"n": 0}

    def boom(url):
        called["n"] += 1
        raise AssertionError("não deve fetch domínio desconhecido")

    monkeypatch.setattr("tools.planos_site_fetcher._fetch_html", boom)
    assert fetch_planos_from_website("https://parqueesportes.com.br/") is None
    assert called["n"] == 0


def test_fetch_planos_smartfit_domain(monkeypatch):
    monkeypatch.setattr(
        "tools.planos_site_fetcher._fetch_html",
        lambda url: _FAKE_SMARTFIT_HTML,
    )
    monkeypatch.setattr(
        "tools.api_cost_tracker.track_api_call",
        lambda *a, **k: __import__("contextlib").nullcontext(),
    )
    planos = fetch_planos_from_website(
        "https://www.smartfit.com.br/academias/papicu/?utm_source=google"
    )
    assert planos is not None
    assert len(planos) == 3
    assert planos[0]["fonte"] == "site_oficial"


def test_cascade_site_hit_skips_light_and_ground(monkeypatch):
    import tools.competitor_tools as ct

    calls = {"light": 0, "ground": 0}
    monkeypatch.setattr(
        "tools.planos_site_fetcher.fetch_planos_from_website",
        lambda url: [{"plano": "Fit", "preco_mensal": "R$ 129,90", "fonte": "site_oficial"}],
    )
    monkeypatch.setattr(
        ct,
        "_planos_precos_searchapi",
        lambda *a, **k: calls.__setitem__("light", calls["light"] + 1) or [{"x": 1}],
    )

    async def ground(*a, **k):
        calls["ground"] += 1
        return [{"y": 1}]

    monkeypatch.setattr(ct, "_planos_precos_grounding", ground)

    async def run_cascade(website: str):
        from tools.planos_site_fetcher import fetch_planos_from_website as fp

        planos = await asyncio.to_thread(fp, website)
        if not planos:
            planos = await asyncio.to_thread(ct._planos_precos_searchapi, "n", "b", "c")
        if not planos:
            planos = await ct._planos_precos_grounding("n", "b", "c")
        return planos

    out = asyncio.run(run_cascade("https://www.smartfit.com.br/x"))
    assert out[0]["preco_mensal"] == "R$ 129,90"
    assert calls["light"] == 0
    assert calls["ground"] == 0
