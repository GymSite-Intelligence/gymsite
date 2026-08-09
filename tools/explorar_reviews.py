"""Reviews do Explorar: só SearchAPI google_maps_reviews. Erro = vazio, sem cache velho."""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("gymsite.explorar.reviews")

_API = "https://www.searchapi.io/api/v1/search"


def parse_searchapi_reviews_payload(data: dict | None) -> list[dict[str, Any]]:
    """Schema SearchAPI google_maps_reviews: `reviews[]` ou `error` → []."""
    if not isinstance(data, dict):
        return []
    if data.get("error"):
        return []
    revs = data.get("reviews")
    if not isinstance(revs, list):
        return []
    return [r for r in revs if isinstance(r, dict)]


def fetch_explorar_reviews(
    *,
    place_id: str,
    data_id: str | None = None,
) -> list[dict[str, Any]]:
    pid = (place_id or "").strip()
    if not pid:
        return []
    key = (os.getenv("SEARCHAPI_KEY") or "").strip()
    if not key:
        return []
    params: dict[str, Any] = {
        "engine": "google_maps_reviews",
        "place_id": pid,
        "sort_by": "lowest_rating",
        "hl": "pt-br",
        "gl": "br",
        "num": 10,
    }
    did = (data_id or "").strip()
    if did:
        params["data_id"] = did
    try:
        with httpx.Client(timeout=25) as client:
            data = client.get(
                _API,
                params=params,
                headers={"Authorization": f"Bearer {key}"},
            ).json()
    except Exception:
        logger.warning("searchapi google_maps_reviews falhou place_id=%s", pid[:24])
        return []
    if not isinstance(data, dict):
        return []
    if data.get("error"):
        logger.info(
            "searchapi google_maps_reviews vazio place_id=%s err=%s",
            pid[:24],
            str(data.get("error"))[:120],
        )
        return []
    return parse_searchapi_reviews_payload(data)
