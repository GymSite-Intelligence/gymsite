"""Planos × preços de BALCÃO a partir do site oficial (A3a tier 0).

Ordem canônica A3a: site HTML/JSON → SearchAPI google_light+Gemini → grounding.
Smart Fit: JSON embutido `plans:[{plan_type, membership.data.original_price}]`.
Wellhub/TotalPass NÃO entram aqui — agregador ≠ balcão.
"""
from __future__ import annotations

import json
import logging
from typing import Callable
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 20.0
_UA = "Mozilla/5.0 (compatible; GymSiteBot/1.0; +https://getgymsite.com.br)"

# plan_type Smart Fit → rótulo balcão
_SMARTFIT_LABEL = {
    "black": "Plano Black",
    "fit": "Plano Fit",
    "smart": "Plano Smart",
}


def _fmt_brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _parse_price_num(raw) -> float | None:
    if raw is None:
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    if v < 10 or v > 5000:
        return None
    return round(v, 2)


def extract_smartfit_plans_html(html: str) -> list[dict] | None:
    """Parse bloco `"plans":[{...}]` da página unidade/planos Smart Fit."""
    if not html or "plan_type" not in html:
        return None
    # Várias ocorrências de "plans" no HTML — pega a que tem plan_type + price.
    plans = None
    start = 0
    while True:
        ini = html.find('"plans"', start)
        if ini < 0:
            break
        bracket = html.find("[", ini)
        if bracket < 0 or bracket - ini > 20:
            start = ini + 7
            continue
        try:
            candidate, _ = json.JSONDecoder().raw_decode(html[bracket:])
        except json.JSONDecodeError:
            start = ini + 7
            continue
        if (
            isinstance(candidate, list)
            and candidate
            and isinstance(candidate[0], dict)
            and "plan_type" in candidate[0]
        ):
            plans = candidate
            break
        start = ini + 7
    if not isinstance(plans, list) or not plans:
        return None

    out: list[dict] = []
    for p in plans:
        if not isinstance(p, dict):
            continue
        ptype = (p.get("plan_type") or "").strip().lower()
        membership = p.get("membership") if isinstance(p.get("membership"), dict) else {}
        data = membership.get("data") if isinstance(membership.get("data"), dict) else {}
        orig = data.get("original_price") if isinstance(data.get("original_price"), dict) else {}
        cur = data.get("current_price") if isinstance(data.get("current_price"), dict) else {}
        mensal = _parse_price_num(orig.get("price")) or _parse_price_num(cur.get("price"))
        if mensal is None:
            continue
        promo = _parse_price_num(cur.get("price"))
        label = _SMARTFIT_LABEL.get(ptype) or f"Plano {ptype.title()}" if ptype else "Plano"
        item: dict = {
            "plano": label,
            "preco_mensal": _fmt_brl(mensal),
            "inclui": [],
            "fidelidade": None,
            "fonte": "site_oficial",
            "fonte_detalhe": "smartfit.com.br HTML plans[]",
        }
        # Promo 1º mês ≠ mensalidade balcão (ticket praça usa original).
        if promo is not None and abs(promo - mensal) > 0.01:
            item["preco_promo_1o_mes"] = _fmt_brl(promo)
            item["inclui"] = [f"Promo 1º mês {_fmt_brl(promo)} (não é mensalidade cheia)"]
        out.append(item)
        if len(out) >= 4:
            break
    return out or None


def _fetch_html(url: str) -> str | None:
    try:
        with httpx.Client(timeout=_TIMEOUT, follow_redirects=True, headers={"User-Agent": _UA}) as c:
            r = c.get(url)
        if r.status_code != 200 or not r.text:
            logger.debug("planos_site HTTP %s %s", r.status_code, url[:80])
            return None
        return r.text
    except Exception as exc:
        logger.debug("planos_site fetch %s: %s", url[:80], type(exc).__name__)
        return None


def _domain(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


_EXTRACTORS: list[tuple[str, Callable[[str], list[dict] | None]]] = [
    ("smartfit.com.br", extract_smartfit_plans_html),
]


def fetch_planos_from_website(website: str | None) -> list[dict] | None:
    """Tier 0 balcão: scrape site oficial se domínio conhecido. None = miss."""
    url = (website or "").strip()
    if not url or not url.startswith("http"):
        return None
    host = _domain(url)
    if not host:
        return None
    extractor = None
    for suffix, fn in _EXTRACTORS:
        if host == suffix or host.endswith("." + suffix):
            extractor = fn
            break
    if extractor is None:
        return None

    from tools.api_cost_tracker import track_api_call

    with track_api_call("planos_precos", "site_oficial_html", 1):
        html = _fetch_html(url)
    if not html:
        return None
    planos = extractor(html)
    if planos:
        logger.info(
            "[planos_site] ok domain=%s n=%s url=%s",
            host,
            len(planos),
            url[:100],
        )
    return planos
