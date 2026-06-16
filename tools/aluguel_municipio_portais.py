"""
Pesquisa de aluguel comercial municipal (Tier 1) — ZAP, Viva Real, OLX.

Escopo: cidade + UF (não bairro). Entrega faixa R$/m² (P25–P75) para o empreendedor,
com mediana usada internamente no A4. Fallback: Tier 2 (Search Grounding) e Tier 3 (ACAD).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from typing import Any

import httpx

# Windows + ADK: sync_api em thread (SelectorEventLoop não suporta subprocess async).
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    PlaywrightTimeout = Exception  # type: ignore[misc, assignment]

logger = logging.getLogger(__name__)

MIN_SAMPLES_ALTA = 5
MIN_SAMPLES_MEDIA = 3
FETCH_TIMEOUT_S = 18.0
_PLAYWRIGHT_TIMEOUT_MS = int(os.environ.get("ALUGUEL_PORTAIS_PLAYWRIGHT_TIMEOUT_MS", "45000"))
_MAX_CONCURRENT = 4
_R_M2_MIN, _R_M2_MAX = 5.0, 500.0


def _env_truthy(name: str, *, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def playwright_forced() -> bool:
    """ALUGUEL_PORTAIS_USE_PLAYWRIGHT=1 — só Chromium (sem httpx)."""
    return _env_truthy("ALUGUEL_PORTAIS_USE_PLAYWRIGHT", default=False)


def playwright_fallback_enabled() -> bool:
    """ALUGUEL_PORTAIS_PLAYWRIGHT_FALLBACK=0 desliga retry após httpx vazio."""
    return _env_truthy("ALUGUEL_PORTAIS_PLAYWRIGHT_FALLBACK", default=True)

_DEFAULT_KEYWORDS = (
    "galpão",
    "galpao",
    "ponto comercial",
    "salão",
    "salao",
    "loja",
)

UF_NOME_SLUG = {
    "AC": "acre",
    "AL": "alagoas",
    "AP": "amapa",
    "AM": "amazonas",
    "BA": "bahia",
    "CE": "ceara",
    "DF": "distrito-federal",
    "ES": "espirito-santo",
    "GO": "goias",
    "MA": "maranhao",
    "MT": "mato-grosso",
    "MS": "mato-grosso-do-sul",
    "MG": "minas-gerais",
    "PA": "para",
    "PB": "paraiba",
    "PR": "parana",
    "PE": "pernambuco",
    "PI": "piaui",
    "RJ": "rio-de-janeiro",
    "RN": "rio-grande-do-norte",
    "RS": "rio-grande-do-sul",
    "RO": "rondonia",
    "RR": "roraima",
    "SC": "santa-catarina",
    "SP": "sao-paulo",
    "SE": "sergipe",
    "TO": "tocantins",
}

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

_RE_PRICE = re.compile(
    r"R\$\s*([\d]{1,3}(?:\.[\d]{3})*(?:,\d{2})?|\d+(?:,\d{2})?)",
    re.IGNORECASE,
)
_RE_AREA = re.compile(r"([\d]{1,3}(?:\.[\d]{3})*|\d+)\s*m[²2]\b", re.IGNORECASE)


def _slug(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[áàâãä]", "a", s)
    s = re.sub(r"[éèêë]", "e", s)
    s = re.sub(r"[íìîï]", "i", s)
    s = re.sub(r"[óòôõö]", "o", s)
    s = re.sub(r"[úùûü]", "u", s)
    s = re.sub(r"[ç]", "c", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _parse_br_money(raw: str) -> float:
    s = (raw or "").strip().replace("R$", "").strip()
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(".", "")
    return float(s)


def _parse_area_m2(text: str) -> float:
    if not text:
        return 0.0
    m = _RE_AREA.search(text)
    if not m:
        return 0.0
    raw = m.group(1).replace(".", "")
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _percentil(valores: list[float], p: float) -> float:
    if not valores:
        return 0.0
    s = sorted(valores)
    if len(s) == 1:
        return round(s[0], 2)
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return round(s[f], 2)
    return round(s[f] + (s[c] - s[f]) * (k - f), 2)


def _mediana(valores: list[float]) -> float:
    return _percentil(valores, 0.5)


def _municipio_parse_area_bounds(area_m2_min: int, area_m2_max: int) -> tuple[int, int]:
    """Amplitude municipal (comercial) — mais ampla que o preset do relatório."""
    lo = max(40, int(area_m2_min * 0.1))
    hi = max(lo + 100, int(area_m2_max * 3))
    return lo, hi


def build_portal_search_urls(
    cidade: str,
    uf: str,
    area_m2_min: int,
    area_m2_max: int,
    keywords: tuple[str, ...] | None = None,
) -> dict[str, list[str]]:
    """
    URLs determinísticas de busca por município (sem hardcode de cidade).
    area_* entra na query string onde o portal suporta filtro de área.
    """
    _ = keywords  # reservado para expansão futura em qs
    uf_up = (uf or "").upper()[:2]
    uf_low = uf_up.lower()
    uf_nome = UF_NOME_SLUG.get(uf_up, _slug(uf))
    cidade_slug = _slug(cidade)
    area_q = f"areaMin={area_m2_min}&areaMax={area_m2_max}"

    zap_base = f"https://www.zapimoveis.com.br/aluguel"
    zap = [
        f"{zap_base}/galpoes-depositos-armazens/{uf_low}+{cidade_slug}/?{area_q}",
        f"{zap_base}/imoveis-comerciais/{uf_low}+{cidade_slug}/?{area_q}",
        f"{zap_base}/pontos-comerciais/{uf_low}+{cidade_slug}/?{area_q}",
    ]

    viva = [
        f"https://www.vivareal.com.br/aluguel/{uf_nome}/{cidade_slug}/imovel-comercial/?{area_q}",
        f"https://www.vivareal.com.br/aluguel/{uf_nome}/{cidade_slug}/galpao-deposito-armazem/?{area_q}",
        f"https://www.vivareal.com.br/aluguel/{uf_nome}/{cidade_slug}/salas-comerciais/?{area_q}",
    ]

    olx_cats = (
        "lojas-salas-e-pontos-comerciais",
        "galpoes-e-depositos",
    )
    # Padrão confirmado em listing_sources.md + imobiliaria_scraper (cidade/estado-uf).
    # Evitar "{cidade}-e-regiao" na listagem — devolve feed regional incorreto.
    olx = [
        f"https://www.olx.com.br/imoveis/aluguel/{cat}/{cidade_slug}/estado-{uf_low}?re={uf_up}&{area_q}"
        for cat in olx_cats
    ]

    return {"zap": zap, "viva": viva, "olx": olx}


# ── Tier 1b: índice do Google via SearchAPI (12/06) ────────────────────────
# Os portais bloqueiam scraping de LISTAGEM (Akamai/JS), mas o Google já
# indexou os anúncios — e os títulos trazem preço+área no padrão do portal
# ("Galpão para alugar, 1200m² por R$ 25.000"). Consultamos o índice via
# SearchAPI (engine=google, site:portal) e extraímos do título/snippet.
# Mesma auditoria (URL real do anúncio), mesmo gate comercial, custo já
# pago no plano full.
_PRECO_RE = re.compile(r"R\$\s?([\d.]{3,12})(?:/m[eê]s|\s|,|$)", re.IGNORECASE)
_AREA_RE = re.compile(r"(\d{2,5})\s?m[²2]\b", re.IGNORECASE)

_SEARCHAPI_PORTAIS = (
    ("zapimoveis.com.br/aluguel", "zap(google)"),
    ("vivareal.com.br/aluguel", "viva(google)"),
    ("olx.com.br", "olx(google)"),
    ("imovelweb.com.br", "imovelweb(google)"),
)
_TERMOS_COMERCIAIS = ("galpão para alugar", "loja para alugar", "salão comercial alugar")

# Locations API (free) — resolve o `location` canônico do Google p/ geo-targeting.
# Sem isso, `detected_location: Desconhecido` e o índice devolve landing pages
# genéricas da categoria (sem preço/área no snippet → descartadas). Cache in-process.
_LOCATION_CACHE: dict[str, str | None] = {}


def _resolver_location_searchapi(cidade: str, uf: str = "") -> str | None:
    """Canonical name do Google p/ (cidade, uf) via Locations API. Free, best-effort."""
    chave = f"{cidade}|{uf}".lower().strip()
    if chave in _LOCATION_CACHE:
        return _LOCATION_CACHE[chave]

    import requests as _rq

    key = (os.getenv("SEARCHAPI_KEY") or "").strip()
    if not key:
        _LOCATION_CACHE[chave] = None
        return None

    termo = f"{cidade} {uf}".strip()
    canonical: str | None = None
    try:
        r = _rq.get(
            "https://www.searchapi.io/api/v1/locations",
            headers={"Authorization": f"Bearer {key}"},
            params={"q": termo, "limit": 5},
            timeout=20,
        )
        r.raise_for_status()
        body = r.json()
        # A API devolve lista (ou {"locations":[...]}). Pega 1º match no Brasil.
        itens = body if isinstance(body, list) else (body.get("locations") or [])
        for it in itens:
            cc = str(it.get("country_code") or it.get("country") or "").upper()
            if cc and cc not in ("BR", "BRAZIL", "BRASIL"):
                continue
            canonical = it.get("canonical_name") or it.get("name")
            if canonical:
                break
    except Exception:
        canonical = None

    _LOCATION_CACHE[chave] = canonical
    return canonical


def _build_queries_aluguel(cidade: str, bairro: str = "") -> list[tuple[str, str]]:
    """Ordena queries: bairro-específico PRIMEIRO (snippets c/ preço/área), depois
    cidade-inteira. Dentro do cap, prioriza o que rende dado — não landing genérica."""
    rounds: list[tuple[str, str]] = []
    bairro = (bairro or "").strip()
    if bairro:
        for dominio, portal in _SEARCHAPI_PORTAIS:
            for termo in _TERMOS_COMERCIAIS:
                rounds.append((f"site:{dominio} {termo} {bairro} {cidade}", portal))
    for dominio, portal in _SEARCHAPI_PORTAIS:
        for termo in _TERMOS_COMERCIAIS:
            rounds.append((f"site:{dominio} {termo} {cidade}", portal))
    return rounds


def _amostras_via_searchapi_google(
    cidade: str,
    uf: str,
    area_m2_min: int,
    area_m2_max: int,
    max_queries: int = 8,
    bairro: str = "",
) -> tuple[list[dict[str, Any]], list[str]]:
    """Colhe amostras de aluguel comercial do índice Google (SearchAPI).

    Retorna (amostras, erros). Best-effort: sem SEARCHAPI_KEY → ([], [...]).
    Quando `bairro` é dado, prioriza queries bairro-específicas (mais preço/área
    no snippet) dentro do mesmo cap de queries — geo via Locations API.
    """
    import requests as _rq

    key = (os.getenv("SEARCHAPI_KEY") or "").strip()
    if not key:
        return [], ["searchapi: SEARCHAPI_KEY ausente"]

    location = _resolver_location_searchapi(cidade, uf)
    amostras: list[dict[str, Any]] = []
    erros: list[str] = []
    vistos: set[str] = set()
    queries_feitas = 0

    for q, portal in _build_queries_aluguel(cidade, bairro):
        if queries_feitas >= max_queries:
            break
        queries_feitas += 1
        try:
            # google_light: mesmos organic_results (title/link/snippet) da
            # spec, mais rápida/barata — suficiente pra busca site:.
            # Paginação por `page` (a spec NÃO tem `num`).
            params = {
                "engine": "google_light",
                "q": q,
                "gl": "br",
                "hl": "pt-br",
                "page": 1,
            }
            if location:
                params["location"] = location
            r = _rq.get(
                "https://www.searchapi.io/api/v1/search",
                headers={"Authorization": f"Bearer {key}"},
                params=params,
                timeout=30,
            )
            r.raise_for_status()
            organicos = r.json().get("organic_results") or []
        except Exception as e:
            erros.append(f"searchapi {portal} '{q}': {type(e).__name__}")
            continue

        for res in organicos:
            url = str(res.get("link") or "")
            if not url or url in vistos:
                continue
            vistos.add(url)
            texto = f"{res.get('title') or ''} {res.get('snippet') or ''}"
            m_preco = _PRECO_RE.search(texto)
            m_area = _AREA_RE.search(texto)
            if not m_preco or not m_area:
                continue
            try:
                preco = float(m_preco.group(1).replace(".", ""))
                area = float(m_area.group(1))
            except ValueError:
                continue
            s = _sample_from_price_area(
                preco, area, url, portal, area_m2_min, area_m2_max
            )
            if s:
                amostras.append(s)

    return amostras, erros


# Gate comercial (12/06): as URLs de busca SÃO de categorias comerciais, mas
# o OLX injeta "anúncios relacionados" RESIDENCIAIS quando a categoria tem
# poucos resultados — apartamentos contaminaram a mediana do Bessa e o proxy
# residencial superestima o aluguel comercial grande em ~2-3x (evidência
# interna: proxy R$ 48-58/m² vs candidatos comerciais reais R$ 15-18/m²).
# Validação POR ANÚNCIO via slug da URL; na dúvida (sem termo nenhum), passa.
_RESIDENCIAL_RE = re.compile(
    r"apartamento|partamento|apto\b|casa-|/casa\b|kitnet|kitinete|quitinete|"
    r"flat\b|cobertura|sobrado|condominio-residencial|quarto[s]?-|residencial|"
    r"mobiliad[oa]",
    re.IGNORECASE,
)
_COMERCIAL_RE = re.compile(
    r"galp[aã]o|loja|sala[s]?-comerc|ponto-comercial|comercial|predio|"
    r"pr[eé]dio|deposito|armaz[eé]m|escritorio|terreno-comercial|"
    r"im[oó]vel-comercial|salao\b|sal[aã]o-",
    re.IGNORECASE,
)


def _eh_anuncio_residencial(url: str) -> bool:
    """True quando o anúncio NÃO pode entrar na mediana comercial.

    Gate v2 (12/06): exige sinal COMERCIAL EXPLÍCITO na URL. A regra antiga
    'na dúvida passa' deixou apartamento sem slug ('aluguel-anual-locacao')
    e typo de anunciante ('partamento') contaminarem a mediana. Com o Tier
    1b (índice Google) garantindo volume comercial, precision > recall.
    """
    u = url or ""
    if _COMERCIAL_RE.search(u):
        return False  # sinal comercial explícito — entra (mesmo dual-use)
    return True  # residencial declarado OU neutro — fora da mediana comercial


def _sample_from_price_area(
    price: float,
    area: float,
    url: str,
    portal: str,
    area_m2_min: int,
    area_m2_max: int,
) -> dict[str, Any] | None:
    if price <= 0 or area <= 0:
        return None
    if area < area_m2_min * 0.5 or area > area_m2_max * 1.5:
        return None
    r_m2 = round(price / area, 2)
    if not (_R_M2_MIN <= r_m2 <= _R_M2_MAX):
        return None
    return {
        "price_reais": round(price, 2),
        "area_m2": round(area, 2),
        "r_m2": r_m2,
        "url": url,
        "portal": portal,
        # marcada aqui, filtrada com contagem em pesquisar_aluguel_municipio
        "categoria": "residencial" if _eh_anuncio_residencial(url) else "comercial",
    }


def _iter_str_values(obj: Any) -> list[str]:
    out: list[str] = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(_iter_str_values(v))
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            out.extend(_iter_str_values(v))
    return out


def _olx_ad_matches_municipio(ad: dict[str, Any], cidade: str, uf: str = "") -> bool:
    """
    Filtro conservador: só aceita anúncios claramente atrelados ao município.

    - Se não receber cidade, nunca filtra (compatibilidade com usos antigos).
    - Procura nome do município em campos de localização (location*, address*, city, neighborhood).
    - Se não encontrar nenhuma string de localização, prefere descartar o anúncio.
    """
    if not cidade:
        return True

    cidade_slug = _slug(cidade)
    if not cidade_slug:
        return True
    cidade_compact = cidade_slug.replace("-", "")
    uf_up = (uf or "").upper()[:2]

    det = ad.get("locationDetails")
    if isinstance(det, dict):
        mun = det.get("municipality") or det.get("municipio")
        if isinstance(mun, str) and mun.strip():
            if cidade_compact in _slug(mun).replace("-", ""):
                return True
            return False

    location_texts: list[str] = []
    for key, val in ad.items():
        k = str(key).lower()
        if any(tok in k for tok in ("location", "address", "city", "state", "neigh", "bairro", "municip")):
            location_texts.extend(_iter_str_values(val))

    # Alguns anúncios trazem o município em campos de título/resumo.
    for k in ("title", "subject", "subtitle"):
        v = ad.get(k)
        if isinstance(v, str):
            location_texts.append(v)

    joined = " ".join(t for t in location_texts if isinstance(t, str)).strip()
    if not joined:
        return False

    loc_slug = _slug(joined)
    loc_compact = loc_slug.replace("-", "")

    # Aceita apenas quando o município aparece explicitamente nos textos de localização.
    if cidade_compact not in loc_compact:
        return False

    # UF é opcional em muitos cards; quando presente e não bate, descartamos.
    if uf_up and any(s for s in location_texts if isinstance(s, str) and uf_up in s.upper()):
        return True
    if uf_up and not any(s for s in location_texts if isinstance(s, str) and uf_up in s.upper()):
        # cidade bateu mas UF nunca aparece — ainda assim aceitamos, pois muitos cards omitem UF.
        return True

    return True


def _parse_olx_nextdata(
    html: str,
    area_m2_min: int,
    area_m2_max: int,
    *,
    cidade: str = "",
    uf: str = "",
) -> list[dict[str, Any]]:
    m = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []

    page_props = (
        data.get("props", {}).get("pageProps", {}) if isinstance(data, dict) else {}
    )
    ads = page_props.get("ads") or []
    out: list[dict[str, Any]] = []
    for ad in ads:
        if not isinstance(ad, dict):
            continue
        if not _olx_ad_matches_municipio(ad, cidade, uf):
            continue
        props = ad.get("properties") or []
        area_raw = ""
        for p in props:
            if isinstance(p, dict) and p.get("name") == "size":
                area_raw = p.get("value") or p.get("label") or ""
                break
        area = _parse_area_m2(str(area_raw))
        price_vals = ad.get("priceValue") or ad.get("price") or ""
        try:
            if isinstance(price_vals, (int, float)):
                price = float(price_vals)
            else:
                price = _parse_br_money(str(price_vals))
        except (TypeError, ValueError):
            price = 0.0
        friendly = ad.get("friendlyUrl") or ad.get("url") or ""
        url = friendly if str(friendly).startswith("http") else f"https://www.olx.com.br{friendly}"
        s = _sample_from_price_area(price, area, url, "olx", area_m2_min, area_m2_max)
        if s:
            out.append(s)
    return out


def _parse_listing_urls(html: str, portal: str) -> list[str]:
    patterns = {
        "zap": r"https://www\.zapimoveis\.com\.br/imovel/[^\"'\s<>]+",
        "viva": r"https://www\.vivareal\.com\.br/imovel/[^\"'\s<>]+",
        "olx": r"https://(?:www\.|[a-z]{2}\.)?olx\.com\.br/[^\"'\s<>]+-\d{8,}",
    }
    pat = patterns.get(portal)
    if not pat:
        return []
    seen: set[str] = set()
    urls: list[str] = []
    for u in re.findall(pat, html, re.IGNORECASE):
        u = u.split("?")[0].rstrip("/")
        if u not in seen:
            seen.add(u)
            urls.append(u)
    return urls[:40]


def _parse_cards_near_urls(
    html: str,
    portal: str,
    area_m2_min: int,
    area_m2_max: int,
) -> list[dict[str, Any]]:
    """Extrai pares preço+área em janelas de texto ao redor de URLs de anúncio."""
    out: list[dict[str, Any]] = []
    for url in _parse_listing_urls(html, portal):
        idx = html.find(url)
        if idx < 0:
            continue
        window = html[max(0, idx - 400) : idx + 400]
        prices = [_parse_br_money(m.group(1)) for m in _RE_PRICE.finditer(window)]
        areas = [_parse_area_m2(m.group(0)) for m in _RE_AREA.finditer(window)]
        if not prices or not areas:
            continue
        price = max(prices)
        area = max(areas)
        s = _sample_from_price_area(price, area, url, portal, area_m2_min, area_m2_max)
        if s:
            out.append(s)
    return out


def parse_listings_html(
    html: str,
    portal: str,
    area_m2_min: int,
    area_m2_max: int,
    *,
    cidade: str = "",
    uf: str = "",
) -> list[dict[str, Any]]:
    if not html:
        return []
    if portal == "olx":
        olx = _parse_olx_nextdata(
            html,
            area_m2_min,
            area_m2_max,
            cidade=cidade,
            uf=uf,
        )
        if olx:
            return olx
    return _parse_cards_near_urls(html, portal, area_m2_min, area_m2_max)


async def _fetch_html(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        r = await client.get(url, follow_redirects=True)
    except (httpx.HTTPError, asyncio.TimeoutError) as exc:
        logger.debug("aluguel_municipio: fetch %s — %s", url[:80], exc)
        return None
    if r.status_code != 200:
        return None
    ct = (r.headers.get("content-type") or "").lower()
    if "text/html" not in ct and "application/xhtml" not in ct:
        return None
    return r.text


async def _fetch_pages_httpx(
    portal_urls: list[tuple[str, str]],
    *,
    timeout_s: float,
) -> dict[str, str | None]:
    sem = asyncio.Semaphore(_MAX_CONCURRENT)
    out: dict[str, str | None] = {}
    headers = {"User-Agent": _USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9"}

    async with httpx.AsyncClient(headers=headers, timeout=timeout_s) as client:

        async def _one(portal: str, url: str) -> None:
            async with sem:
                out[url] = await _fetch_html(client, url)

        await asyncio.gather(*[_one(p, u) for p, u in portal_urls])
    return out


def _fetch_pages_playwright_sync(
    portal_urls: list[tuple[str, str]],
    *,
    timeout_ms: int = _PLAYWRIGHT_TIMEOUT_MS,
) -> dict[str, str | None]:
    """Chromium síncrono — roda em asyncio.to_thread (Windows + ADK)."""
    if not PLAYWRIGHT_AVAILABLE or not portal_urls:
        return {url: None for _, url in portal_urls}

    out: dict[str, str | None] = {url: None for _, url in portal_urls}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=_USER_AGENT,
                locale="pt-BR",
                viewport={"width": 1280, "height": 900},
            )
            try:
                for portal, url in portal_urls:
                    page = context.new_page()
                    try:
                        page.goto(
                            url,
                            wait_until="domcontentloaded",
                            timeout=timeout_ms,
                        )
                        if portal == "olx":
                            try:
                                page.wait_for_function(
                                    "window.__NEXT_DATA__?.props?.pageProps?.totalOfAds > 0",
                                    timeout=timeout_ms,
                                )
                            except PlaywrightTimeout:
                                pass
                        else:
                            time.sleep(1.5)
                        out[url] = page.content()
                    except Exception as exc:
                        logger.debug(
                            "aluguel_municipio playwright %s — %s",
                            url[:80],
                            exc,
                        )
                    finally:
                        page.close()
            finally:
                browser.close()
    except Exception as exc:
        logger.warning("aluguel_municipio: sessão Playwright falhou — %s", exc)
    return out


async def _fetch_pages_playwright(
    portal_urls: list[tuple[str, str]],
    *,
    timeout_ms: int = _PLAYWRIGHT_TIMEOUT_MS,
) -> dict[str, str | None]:
    """Wrapper async — delega ao sync em thread separada."""
    return await asyncio.to_thread(
        _fetch_pages_playwright_sync,
        portal_urls,
        timeout_ms=timeout_ms,
    )


def _dedup_samples(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dedup: dict[str, dict[str, Any]] = {}
    for s in samples:
        key = s.get("url") or f"{s['portal']}:{s['r_m2']}:{s['area_m2']}"
        dedup[key] = s
    return list(dedup.values())


def _parse_html_map(
    portal_urls: list[tuple[str, str]],
    html_by_url: dict[str, str | None],
    *,
    area_m2_min: int,
    area_m2_max: int,
    via: str,
    cidade: str = "",
    uf: str = "",
) -> tuple[list[dict[str, Any]], list[str]]:
    samples: list[dict[str, Any]] = []
    erros: list[str] = []
    for portal, url in portal_urls:
        html = html_by_url.get(url)
        if not html:
            erros.append(f"{portal}: sem HTML [{via}] ({url[:70]}…)")
            continue
        parsed = parse_listings_html(
            html,
            portal,
            area_m2_min,
            area_m2_max,
            cidade=cidade,
            uf=uf,
        )
        if not parsed:
            erros.append(f"{portal}: 0 anúncios parseados [{via}] ({url[:70]}…)")
        samples.extend(parsed)
    return samples, erros


async def fetch_and_parse_listings(
    urls_by_portal: dict[str, list[str]],
    *,
    area_m2_min: int,
    area_m2_max: int,
    timeout_s: float = FETCH_TIMEOUT_S,
    use_playwright: bool | None = None,
    cidade: str = "",
    uf: str = "",
) -> tuple[list[dict[str, Any]], list[str], str]:
    """
    Busca e parseia URLs. Retorna (amostras, erros, transport).

    use_playwright: True = só Chromium; False = só httpx; None = auto
    (env ALUGUEL_PORTAIS_USE_PLAYWRIGHT ou fallback se httpx retornar 0).
    """
    portal_urls = [
        (portal, url)
        for portal, urls in urls_by_portal.items()
        for url in urls
    ]
    if not portal_urls:
        return [], [], "none"

    force_pw = playwright_forced() if use_playwright is None else use_playwright
    erros: list[str] = []

    if force_pw:
        if not PLAYWRIGHT_AVAILABLE:
            return [], ["playwright_nao_instalado"], "playwright"
        html_map = await _fetch_pages_playwright(portal_urls)
        samples, parse_erros = _parse_html_map(
            portal_urls,
            html_map,
            area_m2_min=area_m2_min,
            area_m2_max=area_m2_max,
            via="playwright",
            cidade=cidade,
            uf=uf,
        )
        return _dedup_samples(samples), erros + parse_erros, "playwright"

    html_map = await _fetch_pages_httpx(portal_urls, timeout_s=timeout_s)
    samples, parse_erros = _parse_html_map(
        portal_urls,
        html_map,
        area_m2_min=area_m2_min,
        area_m2_max=area_m2_max,
        via="httpx",
        cidade=cidade,
        uf=uf,
    )
    erros.extend(parse_erros)

    if (
        not samples
        and use_playwright is not False
        and playwright_fallback_enabled()
        and PLAYWRIGHT_AVAILABLE
    ):
        html_pw = await _fetch_pages_playwright(portal_urls)
        samples_pw, parse_pw = _parse_html_map(
            portal_urls,
            html_pw,
            area_m2_min=area_m2_min,
            area_m2_max=area_m2_max,
            via="playwright",
            cidade=cidade,
            uf=uf,
        )
        if samples_pw:
            return _dedup_samples(samples_pw), erros + parse_pw, "httpx+playwright"
        erros.extend(parse_pw)

    return _dedup_samples(samples), erros, "httpx"


def _classificar_vs_benchmark(mediana: float, cidade: str) -> str:
    from tools.financial_tools import BENCHMARKS_ALUGUEL

    bench = BENCHMARKS_ALUGUEL.get(cidade) or BENCHMARKS_ALUGUEL["default"]
    ref = float(bench["med"])
    if mediana < ref * 0.85:
        return "abaixo_do_benchmark"
    if mediana > ref * 1.15:
        return "acima_do_benchmark"
    return "na_faixa_do_benchmark"


def aggregate_municipio(
    samples: list[dict[str, Any]],
    *,
    cidade: str,
    uf: str = "",
) -> dict[str, Any]:
    valores = [float(s["r_m2"]) for s in samples if s.get("r_m2")]
    n = len(valores)

    if n == 0:
        return {
            "faixa_rs_m2": {"p25": 0.0, "mediana": 0.0, "p75": 0.0, "baixo": 0.0, "tipico": 0.0, "alto": 0.0},
            "n_validos": 0,
            "confianca": "baixa",
            "classificacao": "sem_dados",
            "exemplos_urls": [],
            "fonte": "Portais municipais (ZAP/Viva/OLX)",
            "aviso": "Nenhum anúncio com preço e área válidos nos portais consultados.",
            "norte": (
                f"Sem anúncios municipais parseáveis em {cidade}"
                f"{f'/{uf}' if uf else ''} — consultar Tier 2 (busca) ou cotação local."
            ),
            "cidade": cidade,
            "uf": uf,
        }

    p25 = _percentil(valores, 0.25)
    med = _mediana(valores)
    p75 = _percentil(valores, 0.75)

    if n >= MIN_SAMPLES_ALTA:
        confianca = "alta"
    elif n >= MIN_SAMPLES_MEDIA:
        confianca = "media"
    else:
        confianca = "baixa"

    classificacao = _classificar_vs_benchmark(med, cidade)
    exemplos = [s["url"] for s in samples if s.get("url")][:5]

    norte = (
        f"Norte de mercado em {cidade}"
        f"{f'/{uf}' if uf else ''}: faixa típica entre R$ {p25:.0f} e R$ {p75:.0f}/m² "
        f"(referência central ~R$ {med:.0f}/m²), com base em {n} anúncios municipais. "
        f"Confiança {confianca} — use como orientação, não cotação pontual."
    )

    return {
        "faixa_rs_m2": {
            "p25": p25,
            "mediana": med,
            "p75": p75,
            "baixo": p25,
            "tipico": med,
            "alto": p75,
        },
        "n_validos": n,
        "confianca": confianca,
        "classificacao": classificacao,
        "exemplos_urls": exemplos,
        "fonte": "Portais municipais (ZAP/Viva/OLX)",
        "aviso": norte,
        "norte": norte,
        "cidade": cidade,
        "uf": uf,
    }


async def pesquisar_aluguel_municipio(
    cidade: str,
    uf: str = "",
    area_m2_min: int = 800,
    area_m2_max: int = 1500,
    keywords: tuple[str, ...] | None = None,
    *,
    bairro: str = "",
    use_playwright: bool | None = None,
) -> dict[str, Any]:
    """
    Tier 1: scrape municipal dos portais. Retorno pronto para A4/A6.
    """
    kw = keywords or _DEFAULT_KEYWORDS
    urls = build_portal_search_urls(cidade, uf, area_m2_min, area_m2_max, kw)
    parse_lo, parse_hi = _municipio_parse_area_bounds(area_m2_min, area_m2_max)
    samples, erros, fetch_transport = await fetch_and_parse_listings(
        urls,
        area_m2_min=parse_lo,
        area_m2_max=parse_hi,
        use_playwright=use_playwright,
        cidade=cidade,
        uf=uf,
    )

    # Tier 1b (12/06): índice Google via SearchAPI — colhe anúncios que o
    # scrape direto perde (Akamai/JS nas listagens). Merge com dedup por URL.
    try:
        from tools.api_cost_tracker import track_api_call

        amostras_idx, erros_idx = await asyncio.to_thread(
            _amostras_via_searchapi_google, cidade, uf, parse_lo, parse_hi, 8, bairro
        )
        with track_api_call("aluguel_tier1b", "searchapi_google_light", 8):
            pass
        urls_existentes = {s.get("url") for s in samples}
        samples += [s for s in amostras_idx if s.get("url") not in urls_existentes]
        erros += erros_idx
    except Exception as e:
        erros.append(f"tier1b searchapi: {type(e).__name__}")

    # GATE COMERCIAL (12/06): anúncio residencial NUNCA entra na mediana —
    # superestima o aluguel comercial grande em ~2-3x. Descartes ficam
    # contados e auditáveis; sem amostras comerciais, o caller cai pro
    # Tier 2 (grounding) em vez de usar proxy residencial silencioso.
    descartadas_residenciais = [s for s in samples if s.get("categoria") == "residencial"]
    samples = [s for s in samples if s.get("categoria") != "residencial"]

    agg = aggregate_municipio(samples, cidade=cidade, uf=uf)
    faixa = agg["faixa_rs_m2"]
    tier1_suficiente = agg["n_validos"] >= MIN_SAMPLES_ALTA

    return {
        "tier": 1,
        "tier1_suficiente": tier1_suficiente,
        "categoria_gate": "comercial",
        "descartadas_residenciais": len(descartadas_residenciais),
        "mediana_r_m2": faixa["mediana"],
        "min_r_m2": faixa["p25"],
        "max_r_m2": faixa["p75"],
        "n_validos": agg["n_validos"],
        "confianca": agg["confianca"],
        "classificacao": agg["classificacao"],
        "exemplos_urls": agg["exemplos_urls"],
        "fonte": agg["fonte"],
        "aviso": agg["aviso"],
        "norte": agg["norte"],
        "faixa_rs_m2": faixa,
        "amostras": samples[:30],
        "urls_consultadas": urls,
        "fetch_transport": fetch_transport,
        "erros": erros[:20],
        "aluguel_municipio_referencia": {
            "faixa_rs_m2": faixa,
            "classificacao": agg["classificacao"],
            "confianca": agg["confianca"],
            "n_amostras": agg["n_validos"],
            "aviso": agg["aviso"],
            "exemplos": agg["exemplos_urls"],
            "fonte": agg["fonte"],
        },
    }


def pesquisar_aluguel_municipio_sync(
    cidade: str,
    uf: str = "",
    area_m2_min: int = 800,
    area_m2_max: int = 1500,
) -> dict[str, Any]:
    return asyncio.run(
        pesquisar_aluguel_municipio(cidade, uf, area_m2_min, area_m2_max)
    )
