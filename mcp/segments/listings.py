"""MCP segmento Listings — imóveis comerciais OLX via SearchAPI google_light."""

from __future__ import annotations

from typing import Any

LISTINGS_TOOLS: list[dict[str, Any]] = [
    {
        "name": "gymsite_listings_buscar",
        "description": (
            "Listings comerciais no bairro (cascata P1): SearchAPI google_light + "
            "geocode Nominatim + ranking por área/preço. ORANGE — não substitui MRLR."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "cidade": {"type": "string"},
                "uf": {"type": "string"},
                "bairro": {"type": "string"},
                "area_m2_min": {"type": "integer", "default": 200},
                "area_m2_max": {"type": "integer", "default": 800},
            },
            "required": ["cidade", "uf", "bairro"],
        },
    },
    {
        "name": "gymsite_listings_searchapi",
        "description": (
            "Busca bruta OLX via SearchAPI google_light (nível 1 cascata). "
            "Sem geocode/ranking — candidatos crus."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "cidade": {"type": "string"},
                "uf": {"type": "string"},
                "bairro": {"type": "string"},
            },
            "required": ["cidade", "uf", "bairro"],
        },
    },
]


def _slim_listing(item: dict) -> dict:
    return {
        "fonte": item.get("fonte"),
        "url": item.get("url") or item.get("listing_url"),
        "titulo": item.get("titulo") or item.get("title"),
        "area_m2": item.get("area_m2"),
        "preco": item.get("preco"),
        "bairro": item.get("bairro"),
        "latitude": item.get("latitude"),
        "longitude": item.get("longitude"),
        "score_listing": item.get("score_listing"),
        "snippet": (item.get("snippet") or "")[:200] or None,
    }


async def handle_listings_buscar(args: dict) -> dict:
    from tools.listing_cascata import buscar_candidatos_cascata

    cidade = args["cidade"]
    uf = args["uf"]
    bairro = args["bairro"]
    area_min = int(args.get("area_m2_min") or 200)
    area_max = int(args.get("area_m2_max") or 800)

    cands = buscar_candidatos_cascata(cidade, bairro, uf, area_min, area_max)
    slim = [_slim_listing(c) for c in cands if isinstance(c, dict)]

    return {
        "status": "ok" if slim else "indisponivel",
        "cidade": cidade,
        "uf": uf,
        "bairro": bairro,
        "area_m2_min": area_min,
        "area_m2_max": area_max,
        "listings_n": len(slim),
        "listings": slim[:15],
        "carimbo": (
            f"{len(slim)} anúncios · SearchAPI google_light + Nominatim · "
            f"faixa {area_min}–{area_max} m² · ORANGE (não MRLR)"
        ),
        "nota": "Aluguel viabilidade = MRLR Tier 0 no A4 — listings são candidatos ORANGE.",
    }


async def handle_listings_searchapi(args: dict) -> dict:
    from tools.listing_cascata import buscar_listings_searchapi, montar_query_otimizada

    cidade = args["cidade"]
    uf = args["uf"]
    bairro = args["bairro"]
    query = montar_query_otimizada(cidade, bairro, uf)
    raw = buscar_listings_searchapi(cidade, bairro, uf)
    slim = [_slim_listing(c) for c in raw if isinstance(c, dict)]

    return {
        "status": "ok" if slim else "indisponivel",
        "query": query,
        "listings_n": len(slim),
        "listings": slim,
        "carimbo": f"{len(slim)} anúncios · SearchAPI google_light · query OLX otimizada",
        "nota": "Sem geocode/ranking — use gymsite_listings_buscar para cascata completa.",
    }


LISTINGS_HANDLERS = {
    "gymsite_listings_buscar": handle_listings_buscar,
    "gymsite_listings_searchapi": handle_listings_searchapi,
}
