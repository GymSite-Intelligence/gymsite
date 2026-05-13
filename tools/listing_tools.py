"""
tools/listing_tools.py — orquestrador de listings comerciais.

Parsing puro + wrapper sync sobre o runner Playwright em
`tools/imobiliaria_scraper.py`. Decisão arquitetural e contexto em
`docs/listing_sources.md` e comentário VEC-386.

Consumido por A1 GeoScout:
    1. Places API identifica zonas comerciais candidatas
    2. fetch_commercial_listings() agrega OLX (Next.js) + ImovelWeb (JSON-LD)
       via Playwright async, retorna deduplicado e ordenado por área
    3. A1 cruza com zonas via geocode

Por que Playwright e não httpx+bs4: ambos os portais bloqueiam httpx por TLS
fingerprinting (HTTP 403 em 2026-05-13), mesmo com headers Chrome completos.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Iterable

from models.schemas import ListingResult
from tools.imobiliaria_scraper import (
    fetch_olx_nextdata,
    fetch_imovelweb_jsonld,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de parsing puro — exports estáveis (smoke test cobre)
# ─────────────────────────────────────────────────────────────────────────────

# Nome por extenso do estado pra ImovelWeb (lowercase sem acento)
UF_NOME_SLUG = {
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
    """Normaliza pra slug de URL (lowercase, sem acento, hifens)."""
    s = (s or "").lower()
    s = re.sub(r"[áàâãä]", "a", s)
    s = re.sub(r"[éèêë]", "e", s)
    s = re.sub(r"[íìîï]", "i", s)
    s = re.sub(r"[óòôõö]", "o", s)
    s = re.sub(r"[úùûü]", "u", s)
    s = re.sub(r"[ç]", "c", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _extract_id(url: str) -> str:
    """Extrai o ID numérico final (9+ dígitos) do URL do anúncio."""
    m = re.search(r"(\d{9,})", url or "")
    return m.group(1) if m else ""


def _parse_area_m2(text: str) -> int:
    """Extrai área em m² de texto livre. Tolera '988m²', '1.500 m2', '500m'."""
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


# ─────────────────────────────────────────────────────────────────────────────
# Dedup + filtros
# ─────────────────────────────────────────────────────────────────────────────

def _dedup_and_filter(
    listings: Iterable[ListingResult],
    area_min: int,
    area_max: int,
) -> list[ListingResult]:
    """Remove duplicatas por listing_id (preferido) ou endereço normalizado;
    filtra fora da faixa [area_min, area_max]; ordena por área decrescente."""
    seen_ids: set[str] = set()
    seen_addr: set[str] = set()
    final: list[ListingResult] = []

    for l in listings:
        if l.area_m2 < area_min or l.area_m2 > area_max:
            continue
        key_id = l.listing_id or ""
        key_addr = l.address.lower()[:40] if l.address else ""

        if key_id and key_id in seen_ids:
            continue
        if key_addr and key_addr in seen_addr:
            continue

        if key_id:
            seen_ids.add(key_id)
        if key_addr:
            seen_addr.add(key_addr)
        final.append(l)

    return sorted(final, key=lambda x: x.area_m2, reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# Orquestrador async — chamado pelo A1 (que já roda em event loop ADK)
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_commercial_listings_async(
    cidade: str,
    estado: str,
    area_min: int = 800,
    area_max: int = 2000,
) -> list[ListingResult]:
    """Async: agrega OLX (lojas + galpões) + ImovelWeb em paralelo.

    Args:
        cidade: nome humano da cidade ("Fortaleza", "São Paulo")
        estado: UF de 2 letras ("CE", "SP")
        area_min/area_max: faixa em m² (default da academia média 1000m²)

    Returns:
        Lista ordenada por área decrescente. Vazia se todas as fontes falharem.
    """
    estado_uf = estado.upper()[:2]
    estado_sigla = estado_uf.lower()
    estado_slug_iw = UF_NOME_SLUG.get(estado_uf, _slug(estado))
    cidade_slug = _slug(cidade)
    cidade_slug_olx = f"{cidade_slug}-e-regiao"

    olx_lojas, olx_galpoes, imovelweb = await asyncio.gather(
        fetch_olx_nextdata(cidade_slug_olx, estado_sigla, "lojas"),
        fetch_olx_nextdata(cidade_slug_olx, estado_sigla, "galpoes"),
        fetch_imovelweb_jsonld(cidade_slug, estado_slug_iw),
        return_exceptions=True,
    )

    all_listings: list[ListingResult] = []
    for batch in (olx_lojas, olx_galpoes, imovelweb):
        if isinstance(batch, Exception):
            logger.warning("listing_tools: fonte falhou — %s", batch)
            continue
        all_listings.extend(batch)

    final = _dedup_and_filter(all_listings, area_min, area_max)
    logger.info(
        "listing_tools: %s/%s — %d brutos, %d após dedup+filtro [%d-%d m²]",
        cidade, estado_uf, len(all_listings), len(final), area_min, area_max,
    )
    return final


def fetch_commercial_listings(
    cidade: str,
    estado: str,
    area_min: int = 800,
    area_max: int = 2000,
) -> list[ListingResult]:
    """Wrapper sync — útil pra scripts e smoke tests. Em produção (A1 ADK),
    chame `fetch_commercial_listings_async` direto pra evitar criar event loop novo."""
    return asyncio.run(
        fetch_commercial_listings_async(cidade, estado, area_min, area_max)
    )
