"""MCP segmento Mercado — concorrência Maps com cache + carimbo."""

from __future__ import annotations

import json
from typing import Any

MERCADO_TOOLS: list[dict[str, Any]] = [
    {
        "name": "gymsite_mercado_concorrentes_bairro",
        "description": (
            "Contagem e lista de concorrentes (academias) em um bairro via SearchAPI google_maps, "
            "com gate bairro+tipo determinístico. Retorna google_n, gated_n, saturação e carimbo."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "cidade": {"type": "string"},
                "uf": {"type": "string"},
                "bairro": {"type": "string"},
                "tipo_negocio": {
                    "type": "string",
                    "description": "academia | crossfit_box | studio_pilates | studio_funcional | outro",
                    "default": "academia",
                },
            },
            "required": ["cidade", "uf", "bairro"],
        },
    },
    {
        "name": "gymsite_mercado_maps_search",
        "description": (
            "Busca bruta google_maps (query livre). Usa cache search_raw. "
            "Retorna slim local_results + metadata — não substitui gate de bairro."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Ex.: academias Cocó Fortaleza CE"},
                "max_results": {"type": "integer", "default": 20},
            },
            "required": ["query"],
        },
    },
]


def _slim_local_result(item: dict) -> dict:
    gps = item.get("gps_coordinates") or {}
    return {
        "place_id": item.get("place_id"),
        "nome": item.get("title"),
        "endereco": item.get("address"),
        "rating": item.get("rating"),
        "num_avaliacoes": item.get("reviews"),
        "lat": gps.get("latitude"),
        "lng": gps.get("longitude"),
        "types": item.get("types") or ([item["type"]] if item.get("type") else []),
        "snippet_review": item.get("review_text"),
    }


async def handle_concorrentes_bairro(args: dict) -> dict:
    from tools.competitor_tools import cross_check_concorrentes_bairro

    out = cross_check_concorrentes_bairro(
        args["cidade"],
        args["uf"],
        args["bairro"],
        args.get("tipo_negocio") or "academia",
    )
    gated = int(out.get("gated_n") or 0)
    if gated >= 12:
        sat = "alta"
    elif gated >= 6:
        sat = "media"
    elif gated >= 1:
        sat = "baixa"
    else:
        sat = "indeterminada"
    out["saturacao"] = sat
    out["carimbo"] = (
        f"{gated} concorrentes · gate bairro+tipo · SearchAPI google_maps · "
        f"query={out.get('query', '')}"
    )
    return out


async def handle_maps_search(args: dict) -> dict:
    from tools.competitor_tools import _searchapi_maps_textsearch

    query = (args.get("query") or "").strip()
    max_results = int(args.get("max_results") or 20)
    if not query:
        return {"status": "erro", "detail": "query vazia"}

    places = _searchapi_maps_textsearch(query, max_results=max_results)
    return {
        "status": "ok",
        "query": query,
        "google_n": len(places),
        "concorrentes": [
            {
                "place_id": p.get("id"),
                "nome": (p.get("displayName") or {}).get("text"),
                "endereco": p.get("formattedAddress"),
                "rating": p.get("rating"),
                "num_avaliacoes": p.get("userRatingCount"),
            }
            for p in places
        ],
        "carimbo": f"{len(places)} resultados · SearchAPI google_maps · query={query}",
        "nota": "Sem gate bairro — use gymsite_mercado_concorrentes_bairro para contagem autoritativa.",
    }


MERCADO_HANDLERS = {
    "gymsite_mercado_concorrentes_bairro": handle_concorrentes_bairro,
    "gymsite_mercado_maps_search": handle_maps_search,
}


def mercado_tool_text(result: Any) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)
