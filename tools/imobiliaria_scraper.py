# tools/imobiliaria_scraper.py
"""
Scraper VivaReal para aluguel comercial — substitui o default R$35/m² hardcoded
do BENCHMARKS_ALUGUEL pela mediana real do mercado por bairro.

Estratégia idêntica ao playwright_enrichment:
sync_api em thread separada via asyncio.to_thread (compatível Windows + ADK).

Fonte: VivaReal (público, listings comerciais filtráveis por área).
URL pattern: https://www.vivareal.com.br/aluguel/<uf-nome>/<cidade-slug>/bairros/<bairro-slug>/imoveis-comerciais/
"""
import asyncio
import re
from typing import Optional

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# UF (sigla) → nome usado no path do VivaReal
UF_NOMES = {
    "AC": "acre", "AL": "alagoas", "AP": "amapa", "AM": "amazonas",
    "BA": "bahia", "CE": "ceara", "DF": "distrito-federal",
    "ES": "espirito-santo", "GO": "goias", "MA": "maranhao",
    "MT": "mato-grosso", "MS": "mato-grosso-do-sul", "MG": "minas-gerais",
    "PA": "para", "PB": "paraiba", "PR": "parana", "PE": "pernambuco",
    "PI": "piaui", "RJ": "rio-de-janeiro", "RN": "rio-grande-do-norte",
    "RS": "rio-grande-do-sul", "RO": "rondonia", "RR": "roraima",
    "SC": "santa-catarina", "SP": "sao-paulo", "SE": "sergipe",
    "TO": "tocantins",
}


def _slug(s: str) -> str:
    """Normaliza para URL do VivaReal: lowercase, sem acento, hifen."""
    s = (s or "").lower()
    s = re.sub(r"[áàâãä]", "a", s)
    s = re.sub(r"[éèêë]", "e", s)
    s = re.sub(r"[íìîï]", "i", s)
    s = re.sub(r"[óòôõö]", "o", s)
    s = re.sub(r"[úùûü]", "u", s)
    s = re.sub(r"[ç]", "c", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _build_vivareal_url(bairro: str, cidade: str, uf: str,
                         area_min: int, area_max: int) -> str:
    """
    Pattern search-based — URLs path-based dão 403 Cloudflare.
    Fonte do filtro de tipo comercial: filtramos no client side via texto do card.
    """
    bairro_q = bairro.replace(" ", "+")
    cidade_q = cidade.replace(" ", "+")
    return (
        f"https://www.vivareal.com.br/aluguel/?"
        f"onde={bairro_q}+-+{cidade_q}+-+{uf.upper()}"
    )


def _parse_preco(texto: str) -> Optional[int]:
    """Extrai inteiro de R$ em '$ 25.000/mês', 'R$ 30.500', etc."""
    if not texto:
        return None
    primeira_parte = texto.split("/")[0]
    nums = re.sub(r"[^\d]", "", primeira_parte)
    if not nums:
        return None
    try:
        return int(nums)
    except ValueError:
        return None


def _parse_area(texto: str) -> Optional[float]:
    """Extrai m² de '1.200 m²' ou '1200m²'."""
    if not texto:
        return None
    t = texto.lower().replace(".", "").replace(",", ".")
    m = re.search(r"(\d+(?:\.\d+)?)\s*m", t)
    if not m:
        return None
    try:
        v = float(m.group(1))
        return v if 100 <= v <= 50000 else None  # sanity check
    except ValueError:
        return None


def _scrape_sync(bairro: str, cidade: str, uf: str,
                  area_min: int, area_max: int, max_listings: int) -> dict:
    """Versão sync — roda em thread separada via asyncio.to_thread."""
    base = {
        "bairro": bairro, "cidade": cidade, "uf": uf,
        "area_filtro_min": area_min, "area_filtro_max": area_max,
        "fonte": "VivaReal",
        "url_consultada": "",
        "n_amostra": 0,
        "listings": [],
        "min_aluguel_m2": None,
        "mediana_aluguel_m2": None,
        "max_aluguel_m2": None,
        "min_aluguel_mensal": None,
        "mediana_aluguel_mensal": None,
        "max_aluguel_mensal": None,
        "status": "ok",
    }

    if not PLAYWRIGHT_AVAILABLE:
        base["status"] = "playwright_nao_instalado"
        return base

    # URL search-based (única que não dá 403 Cloudflare)
    url = _build_vivareal_url(bairro, cidade, uf, area_min, area_max)
    base["url_consultada"] = url

    # Keywords pra identificar listings COMERCIAIS no texto do card
    # (a URL search-based traz comercial + residencial; filtramos aqui)
    PALAVRAS_COMERCIAIS = [
        "comercial", "loja", "sala", "galpão", "galpao", "ponto comercial",
        "área comercial", "area comercial", "kitnet comercial",
        "imóvel comercial", "imovel comercial", "salão", "salao",
    ]

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/121.0.0.0 Safari/537.36"
                ),
                locale="pt-BR",
                viewport={"width": 1280, "height": 900},
            )
            page = context.new_page()

            try:
                page.goto(url, timeout=30000, wait_until="networkidle")
            except PlaywrightTimeout:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")

            page.wait_for_timeout(3000)

            # Seletor que funciona na URL search-based (descoberto empiricamente)
            cards = page.locator("article")
            if cards.count() == 0:
                cards = page.locator("[data-cy*='property']")

            if not cards or cards.count() == 0:
                base["status"] = "selectors_falharam_ou_sem_listings"
                browser.close()
                return base

            count = min(cards.count(), max_listings)
            listings = []

            for i in range(count):
                card = cards.nth(i)
                try:
                    # Texto integral do card — mais confiável que seletores específicos
                    full_text = card.inner_text(timeout=1500) or ""
                    full_text_low = full_text.lower()

                    # Filtra só comerciais — pula apartamentos/casas residenciais
                    is_comercial = any(p in full_text_low for p in PALAVRAS_COMERCIAIS)
                    is_residencial = any(p in full_text_low for p in [
                        "quarto", "dormitório", "dormitorio", "apartamento", "apto",
                        "casa", "kitnet residencial", "studio residencial"
                    ])
                    if is_residencial and not is_comercial:
                        continue

                    # Extrai preço (linha que tem "R$" e geralmente é a maior)
                    precos_match = re.findall(r"R\$\s*[\d.,]+", full_text)
                    preco = None
                    for pm in precos_match:
                        v = _parse_preco(pm)
                        # Pula valores baixos que são IPTU/condomínio (geralmente <2k)
                        if v and v >= 800:
                            preco = v
                            break

                    # Extrai área
                    area = _parse_area(full_text)

                    # Endereço — tipicamente em h2/h3 ou span com "endereço"
                    endereco_txt = ""
                    for sel in ["h2", "h3", "[class*='address']", "[class*='location']"]:
                        loc = card.locator(sel).first
                        if loc.count() > 0:
                            try:
                                endereco_txt = (loc.text_content(timeout=500) or "").strip()
                                if endereco_txt and len(endereco_txt) > 5:
                                    break
                            except Exception:
                                pass

                    if preco and area and area > 0 and preco > 500:
                        # Filtra por range de área se especificado
                        if area_min <= area <= area_max or area_min == 0:
                            listings.append({
                                "preco_mensal": preco,
                                "area_m2": area,
                                "preco_m2": round(preco / area, 2),
                                "endereco": endereco_txt[:200],
                                "comercial_confirmado": is_comercial,
                            })
                except Exception:
                    continue

            browser.close()

            if listings:
                # Estatísticas
                precos_m2 = sorted([l["preco_m2"] for l in listings])
                precos_total = sorted([l["preco_mensal"] for l in listings])
                meio = len(precos_m2) // 2
                base["listings"] = sorted(listings, key=lambda x: x["preco_m2"])[:5]
                base["n_amostra"] = len(listings)
                base["min_aluguel_m2"] = precos_m2[0]
                base["mediana_aluguel_m2"] = precos_m2[meio]
                base["max_aluguel_m2"] = precos_m2[-1]
                base["min_aluguel_mensal"] = precos_total[0]
                base["mediana_aluguel_mensal"] = precos_total[meio]
                base["max_aluguel_mensal"] = precos_total[-1]
            else:
                base["status"] = "extracao_falhou_zero_listings_validos"

    except Exception as e:
        base["status"] = f"error: {str(e)[:300]}"

    return base


async def buscar_aluguel_comercial(
    bairro: str,
    cidade: str,
    uf: str,
    area_min: int = 1000,
    area_max: int = 1500,
) -> dict:
    """
    Pesquisa aluguel comercial real no VivaReal para o bairro/cidade especificados.

    Retorna estatísticas R$/m² mensal e top 5 listings (sempre — mesmo se falhar
    retorna dict com status). Usar `mediana_aluguel_m2` como input pro
    cálculo de viabilidade financeira em vez do default R$35/m².

    Args:
        bairro: ex "Meireles"
        cidade: ex "Fortaleza"
        uf: sigla, ex "CE"
        area_min: filtro área mínima em m² (default 1000)
        area_max: filtro área máxima em m² (default 1500)

    Returns:
        dict com chaves: bairro, cidade, uf, mediana_aluguel_m2,
        min_aluguel_m2, max_aluguel_m2, n_amostra, listings, status
    """
    try:
        return await asyncio.to_thread(
            _scrape_sync, bairro, cidade, uf, area_min, area_max, 20
        )
    except Exception as e:
        return {
            "bairro": bairro, "cidade": cidade, "uf": uf,
            "status": f"thread_error: {str(e)[:200]}",
            "n_amostra": 0,
            "listings": [],
            "mediana_aluguel_m2": None,
        }
