"""MCP segmento Reviews — google_maps_reviews + classificação dores determinística."""

from __future__ import annotations

from typing import Any

REVIEWS_TOOLS: list[dict[str, Any]] = [
    {
        "name": "gymsite_reviews_place",
        "description": (
            "Reviews de um concorrente (place_id) via SearchAPI google_maps_reviews "
            "com cache cache_reviews. Retorna amostra processada + fonte."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "place_id": {"type": "string"},
                "nome": {"type": "string", "description": "Nome do concorrente (opcional)"},
                "max_reviews": {"type": "integer", "default": 5},
            },
            "required": ["place_id"],
        },
    },
    {
        "name": "gymsite_reviews_dores_bairro",
        "description": (
            "Dores recorrentes no bairro: gate concorrentes + reviews SearchAPI + "
            "classificação determinística + gap competitivo. Números com carimbo."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "cidade": {"type": "string"},
                "uf": {"type": "string"},
                "bairro": {"type": "string"},
                "tipo_negocio": {
                    "type": "string",
                    "default": "academia",
                    "description": "academia | crossfit_box | studio_pilates | studio_funcional | outro",
                },
                "max_concorrentes": {
                    "type": "integer",
                    "default": 10,
                    "description": "Teto de chamadas reviews (custo API)",
                },
            },
            "required": ["cidade", "uf", "bairro"],
        },
    },
]


async def handle_reviews_place(args: dict) -> dict:
    from tools.competitor_tools import _reviews_searchapi_card, buscar_reviews_academia

    place_id = (args.get("place_id") or "").strip()
    nome = (args.get("nome") or "").strip()
    max_reviews = int(args.get("max_reviews") or 5)
    if not place_id:
        return {"status": "erro", "detail": "place_id vazio"}

    card = _reviews_searchapi_card(place_id, max_reviews=max_reviews)
    if card:
        out = {
            "status": "ok",
            "place_id": place_id,
            "nome": nome,
            "reviews": card,
            "total_reviews_analisados": len(card),
            "fonte_reviews": "searchapi",
        }
    else:
        out = buscar_reviews_academia(place_id, nome)
        out["status"] = "ok" if out.get("reviews") else "indisponivel"

    n = int(out.get("total_reviews_analisados") or len(out.get("reviews") or []))
    fonte = out.get("fonte_reviews") or "searchapi|places"
    out["carimbo"] = f"{n} reviews · {fonte} · place_id={place_id}"
    return out


async def handle_dores_bairro(args: dict) -> dict:
    from tools.competitor_tools import (
        analisar_gap_competitivo,
        buscar_reviews_academia,
        classificar_dores_reviews_deterministico,
        cross_check_concorrentes_bairro,
    )

    cidade = args["cidade"]
    uf = args["uf"]
    bairro = args["bairro"]
    tipo = args.get("tipo_negocio") or "academia"
    max_n = max(1, min(int(args.get("max_concorrentes") or 10), 20))

    mercado = cross_check_concorrentes_bairro(cidade, uf, bairro, tipo)
    if mercado.get("status") == "indisponivel":
        return {
            "status": "indisponivel",
            "gated_n": 0,
            "concorrentes_com_reviews": 0,
            "gap": analisar_gap_competitivo([], bairro=bairro),
            "carimbo": "0 reviews · SearchAPI indisponível",
        }

    com_reviews: list[dict] = []
    for c in (mercado.get("no_bairro") or [])[:max_n]:
        if not isinstance(c, dict):
            continue
        pid = (c.get("place_id") or "").strip()
        if not pid:
            continue
        rev = buscar_reviews_academia(pid, c.get("nome") or "")
        reviews = rev.get("reviews") or []
        if not reviews:
            continue
        com_reviews.append({
            "place_id": pid,
            "nome": c.get("nome") or rev.get("nome") or "",
            "rating_geral": rev.get("rating_geral") or c.get("rating"),
            "reviews": reviews,
        })

    classificar_dores_reviews_deterministico(com_reviews)
    gap = analisar_gap_competitivo(com_reviews, bairro=bairro)
    gated = int(mercado.get("gated_n") or 0)

    return {
        "status": "ok",
        "query": mercado.get("query"),
        "gated_n": gated,
        "concorrentes_com_reviews": len(com_reviews),
        "gap": gap,
        "carimbo": (
            f"{len(com_reviews)} perfis c/ reviews · {gated} gated · "
            f"SearchAPI google_maps_reviews · gate bairro+tipo · query={mercado.get('query', '')}"
        ),
    }


REVIEWS_HANDLERS = {
    "gymsite_reviews_place": handle_reviews_place,
    "gymsite_reviews_dores_bairro": handle_dores_bairro,
}
