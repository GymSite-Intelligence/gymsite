"""
tools/imobiliaria_scraper.py — runner Playwright async pra portais imobiliários.

⚠️ Histórico: este arquivo era um scraper VivaReal sync. Em 2026-05-13 foi
re-proposto como abordagem httpx+bs4 contra OLX+ImovelWeb (ver docs/listing_sources.md),
mas testes ao vivo mostraram 403 nos 2 portais (TLS fingerprinting). Playwright
voltou a ser necessário — não pra VivaReal (continua aposentado por instabilidade),
mas pra OLX e ImovelWeb.

Estratégia atual:
- **OLX**: Next.js com SSR. `__NEXT_DATA__` está embedded mas hydration JS aplica
  o filtro de categoria. Esperamos `totalOfAds > 0` e extraímos via `page.evaluate()`.
- **ImovelWeb**: stack legada (naventcdn) sem Next. JSON-LD `RealEstateListing`
  tem url+description+location dos 30 itens; preço e área ficam só no DOM. Merge
  por índice posicional.

Consumido por `tools/listing_tools.py` (wrapper sync + orquestração + dedup).
"""
from __future__ import annotations

import logging
import re
from typing import Any

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

from models.schemas import ListingResult

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers (duplicam parsing puro de listing_tools.py pra evitar import circular)
# ─────────────────────────────────────────────────────────────────────────────

def _extract_id(url: str) -> str:
    m = re.search(r"(\d{9,})", url or "")
    return m.group(1) if m else ""


def _parse_area_m2(text: str) -> int:
    if not text:
        return 0
    m = re.search(r"(\d[\d\.]*)\s*m[²2]?", text)
    if not m:
        m = re.search(r"(\d[\d\.]+)", text)
    if not m:
        return 0
    try:
        return int(m.group(1).replace(".", ""))
    except (ValueError, AttributeError):
        return 0


def _olx_properties_lookup(properties: list[dict], key: str) -> str:
    """OLX retorna properties=[{name, value, label}, ...]. Acha por name."""
    for p in properties or []:
        if p.get("name") == key:
            return p.get("value", "") or p.get("label", "")
    return ""


def _infer_onr_type(title: str, extra_text: str = "") -> tuple[int | None, str | None]:
    text = f"{title} {extra_text}".lower()
    if re.search(r"galp[aã]o|deposito|depósito|armaz[eé]m", text):
        return 31, "Galpão"
    if re.search(r"pr[eé]dio|edif[ií]cio\s+inteiro", text):
        return 33, "Prédio Comercial"
    if re.search(r"loja|ponto\s+comercial|box", text):
        return 15, "Loja"
    if re.search(r"sala\s+comercial|sala", text):
        return 17, "Sala"
    if re.search(r"terreno|lote", text):
        return 71, "Terreno/Fração"
    return None, None



# ─────────────────────────────────────────────────────────────────────────────
# OLX — extrai __NEXT_DATA__ pós-hydration
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_olx_nextdata(
    cidade_slug: str,           # "fortaleza-e-regiao"
    estado_sigla: str,          # "ce" (lowercase)
    category: str = "lojas",    # "lojas" | "galpoes"
    timeout_ms: int = 45000,
) -> list[ListingResult]:
    """Extrai listings da OLX via __NEXT_DATA__ no Chromium após hydration."""
    olx_cats = {
        "lojas": "lojas-salas-e-pontos-comerciais",
        "galpoes": "galpoes-e-depositos",
    }
    cat = olx_cats.get(category, olx_cats["lojas"])
    url = (
        f"https://www.olx.com.br/imoveis/aluguel/{cat}/"
        f"{cidade_slug}/estado-{estado_sigla}"
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            locale="pt-BR",
        )
        page = await context.new_page()
        try:
            # `domcontentloaded` é mais rápido que `networkidle` — basta o
            # script `__NEXT_DATA__` ter aparecido pra extrair.
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            await page.wait_for_function(
                "window.__NEXT_DATA__?.props?.pageProps?.totalOfAds > 0",
                timeout=timeout_ms,
            )
            page_props: dict[str, Any] = await page.evaluate(
                "() => window.__NEXT_DATA__.props.pageProps"
            )
        except PlaywrightTimeout as e:
            logger.warning("olx: timeout esperando hydration em %s — %s", url, e)
            await browser.close()
            return []
        except Exception as e:
            logger.warning("olx: falha %s — %s", url, e)
            await browser.close()
            return []
        finally:
            await browser.close()

    ads = page_props.get("ads", []) or []
    results: list[ListingResult] = []

    for ad in ads:
        try:
            list_id = str(ad.get("listId", "") or "")
            friendly_url = ad.get("friendlyUrl") or ad.get("url") or ""
            props = ad.get("properties", []) or []

            area_raw = _olx_properties_lookup(props, "size")
            area_m2 = _parse_area_m2(area_raw)

            location = ad.get("locationDetails", {}) or {}
            bairro = location.get("neighbourhood") or ""
            cidade = location.get("municipality") or ""
            uf = location.get("uf") or ""
            address = ", ".join([x for x in (bairro, cidade, uf) if x])

            price_value = ad.get("priceValue") or ad.get("price") or ""
            price_raw = str(price_value)

            re_type = _olx_properties_lookup(props, "re_type")
            property_type = "loja" if "loja" in re_type.lower() else (
                "galpao" if "galp" in re_type.lower() else "comercial"
            )
            subject = str(ad.get("subject", ""))
            onr_code, onr_label = _infer_onr_type(subject, re_type)

            results.append(ListingResult(
                source="olx",
                title=subject,
                price_raw=price_raw,
                area_m2=area_m2,
                address=address,
                listing_url=friendly_url,
                listing_id=list_id or _extract_id(friendly_url),
                source_url=url,
                property_type=property_type,
                tipo_imovel_codigo_onr=onr_code,
                tipo_imovel_label=onr_label,
                modalidade="locacao"
            ))
        except Exception as e:
            logger.debug("olx: ad ignorado — %s", e)
            continue

    logger.info("olx: %s/%s/%s → %d ads", cidade_slug, estado_sigla, category, len(results))
    return results


# ─────────────────────────────────────────────────────────────────────────────
# ImovelWeb — JSON-LD + DOM merge
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_imovelweb_jsonld(
    cidade_slug: str,           # "fortaleza"
    estado_slug: str,           # "ceara"
    timeout_ms: int = 30000,
) -> list[ListingResult]:
    """Extrai listings do ImovelWeb via DOM dos cards (atributos data-* + features).

    Inspeção 2026-05-13 mostrou: o JSON-LD na página tem só 30 itens parciais,
    mas o DOM tem ~420 cards visíveis (incluindo "patrocinados"). Cada card
    expõe atributos estáveis:
      - data-id="3032295652"               → listing_id
      - data-to-posting="/propriedades/..."  → URL relativa do anúncio
      - data-qa="posting PROPERTY"          → seletor estável
      - [class*='features'] → "988 m² tot."  → área
      - [class*='price']    → "R$ 9.500"     → preço
      - [class*='location'] → endereço
    """
    url = (
        f"https://www.imovelweb.com.br/comerciais-aluguel-"
        f"{estado_slug}-{cidade_slug}.html"
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            locale="pt-BR",
        )
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

            # Cloudflare challenge — observado em SP capital, não em CE/PR.
            # Playwright headless padrão tem navigator.webdriver=true, detectável.
            # Falha graciosa: retorna [] e A1 segue com OLX como fonte única.
            page_title = (await page.title()) or ""
            if "Just a moment" in page_title or "cf_chl_" in page.url:
                logger.warning(
                    "imovelweb: Cloudflare challenge bloqueou %s — "
                    "fallback pra OLX-only (considerar playwright-stealth)",
                    url,
                )
                await browser.close()
                return []

            try:
                await page.wait_for_selector(
                    "[data-qa*='posting']", timeout=timeout_ms,
                )
            except PlaywrightTimeout:
                logger.warning("imovelweb: timeout esperando posting em %s", url)

            cards: list[dict] = await page.evaluate("""() => {
                const out = [];
                document.querySelectorAll(
                    "[data-qa*='posting'][data-id]"
                ).forEach(card => {
                    out.push({
                        data_id:    card.getAttribute('data-id') || '',
                        data_href:  card.getAttribute('data-to-posting') || '',
                        title:      card.querySelector('h2, h3, [class*="title"]')?.innerText || '',
                        price:      card.querySelector('[class*="price"], [class*="Price"]')?.innerText || '',
                        features:   card.querySelector('[class*="features"], [class*="Features"]')?.innerText || '',
                        address:    card.querySelector('[class*="location"], [class*="Location"]')?.innerText || '',
                        description: card.querySelector('h3 + p, [class*="description"]')?.innerText || '',
                    });
                });
                return out;
            }""")
        except Exception as e:
            logger.warning("imovelweb: falha %s — %s", url, e)
            await browser.close()
            return []
        finally:
            await browser.close()

    results: list[ListingResult] = []
    for c in cards:
        href_raw = c.get("data_href") or ""
        # data-to-posting tem query params (?n_src=Listado...) — strip pra URL limpa
        href_clean = href_raw.split("?")[0]
        listing_url = (
            f"https://www.imovelweb.com.br{href_clean}"
            if href_clean.startswith("/") else href_clean
        )

        listing_id = c.get("data_id") or _extract_id(listing_url)
        area_m2 = _parse_area_m2(c.get("features", ""))

        if not listing_url and area_m2 == 0:
            continue

        title = str(c.get("title", ""))
        desc = str(c.get("description", ""))
        onr_code, onr_label = _infer_onr_type(title, desc)

        results.append(ListingResult(
            source="imovelweb",
            title=title,
            price_raw=str(c.get("price", "")),
            area_m2=area_m2,
            address=str(c.get("address", "")),
            listing_url=listing_url,
            listing_id=str(listing_id),
            source_url=url,
            description=desc[:300],
            tipo_imovel_codigo_onr=onr_code,
            tipo_imovel_label=onr_label,
            modalidade="locacao"
        ))

    logger.info(
        "imovelweb: %s/%s → cards=%d → %d listings",
        cidade_slug, estado_slug, len(cards), len(results),
    )
    return results
