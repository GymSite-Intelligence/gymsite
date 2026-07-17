"""SearchAPI engine=google_maps_place — 1 call, cache compartilhado (pico + reviews).

Fonte canônica do bundle place: popular_times + review_results + website/hours.
Reviews engine (google_maps_reviews) só como fallback se place sem review_results.

Cache SB grava payload SLIM (sem images/posts/thumbnails) — fat payload estourava
upsert silencioso no worker → double call place por gym.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_SOURCE = "searchapi_google_maps_place"

# Campos place_result usados por pico/reviews/contato A3a. Resto (images, posts,
# people_also_search_for, at_this_place) infla jsonb e quebra upsert no Cloud Run.
_PLACE_KEEP = (
    "place_id",
    "data_id",
    "kgmid",
    "title",
    "address",
    "phone",
    "website",
    "domain",
    "rating",
    "reviews",
    "reviews_histogram",
    "gps_coordinates",
    "type",
    "types",
    "open_state",
    "hours",
    "open_hours",
    "timezone",
    "thumbnail",
    "price",
    "plus_code",
    "located_in",
    "booking_link",
    "popular_times",
)

_MAX_CACHED_REVIEWS = 20


def _place_result(raw: dict | None) -> dict:
    if not isinstance(raw, dict):
        return {}
    pr = raw.get("place_result")
    return pr if isinstance(pr, dict) else raw


def _slim_review(rev: dict) -> dict:
    raw_user = rev.get("user")
    user: dict[str, Any] = raw_user if isinstance(raw_user, dict) else {}
    texto = (rev.get("description") or rev.get("text") or rev.get("snippet") or "").strip()
    return {
        "review_id": rev.get("review_id"),
        "rating": rev.get("rating"),
        "description": texto,
        "date": rev.get("date") or "",
        "user": {"name": (user.get("name") or "Anônimo")},
    }


def slim_maps_place_payload(raw: dict) -> dict:
    """Corta mídia/metadata; mantém shape SearchAPI (place_result + search_parameters)."""
    if not isinstance(raw, dict):
        return {}
    pr = _place_result(raw)
    slim_pr: dict[str, Any] = {k: pr[k] for k in _PLACE_KEEP if k in pr and pr[k] is not None}

    rr = pr.get("review_results")
    if isinstance(rr, dict):
        raw_reviews = rr.get("reviews")
        reviews_in: list = raw_reviews if isinstance(raw_reviews, list) else []
        slim_rr: dict[str, Any] = {
            "reviews": [
                _slim_review(r)
                for r in reviews_in[:_MAX_CACHED_REVIEWS]
                if isinstance(r, dict)
            ],
        }
        summaries = rr.get("summaries")
        if isinstance(summaries, list) and summaries:
            slim_rr["summaries"] = [s for s in summaries[:5] if isinstance(s, str)]
        slim_pr["review_results"] = slim_rr

    out: dict[str, Any] = {"place_result": slim_pr}
    sp = raw.get("search_parameters")
    if isinstance(sp, dict):
        out["search_parameters"] = {
            k: sp[k] for k in ("engine", "place_id", "hl", "gl") if k in sp
        }
    return out


def _payload_approx_bytes(payload: dict) -> int:
    try:
        return len(json.dumps(payload, ensure_ascii=False, default=str))
    except Exception:
        return -1


def get_cached_maps_place(place_id: str) -> dict | None:
    """Hit cache_places_details (TTL). Retorna payload cru SearchAPI ou None."""
    if not place_id:
        return None
    try:
        from tools.cache_store import get_places_details

        hit = get_places_details(place_id)
        if not hit.hit or not isinstance(hit.payload, dict):
            return None
        payload = hit.payload.get("payload")
        if not isinstance(payload, dict):
            return None
        if payload.get("place_result") or payload.get("search_parameters") or payload.get("popular_times"):
            return payload
        return None
    except Exception:
        return None


def fetch_maps_place_network(place_id: str) -> dict | None:
    """GET SearchAPI google_maps_place. None se sem key/erro/429."""
    if not place_id:
        return None
    key = (os.getenv("SEARCHAPI_KEY") or "").strip()
    if not key:
        return None
    try:
        import requests

        from tools.api_cost_tracker import track_api_call

        with track_api_call("searchapi_maps_place", "searchapi_google_maps_place", 1):
            resp = requests.get(
                "https://www.searchapi.io/api/v1/search",
                params={
                    "engine": "google_maps_place",
                    "place_id": place_id,
                    "hl": "pt",
                    "gl": "br",
                    "api_key": key,
                },
                timeout=20,
            )
        if resp.status_code == 429:
            logger.warning("searchapi google_maps_place 429 place_id=%s", place_id)
            return None
        if resp.status_code != 200:
            logger.warning(
                "searchapi google_maps_place HTTP %s place_id=%s",
                resp.status_code,
                place_id,
            )
            return None
        data = resp.json()
        return data if isinstance(data, dict) else None
    except Exception as exc:
        logger.debug("searchapi google_maps_place %s: %s", place_id, exc)
        return None


def set_maps_place_cache(place_id: str, raw: dict) -> bool:
    """Upsert slim em cache_places_details. False se SB off ou upsert falha."""
    if not place_id or not isinstance(raw, dict):
        return False
    slim = slim_maps_place_payload(raw)
    if not slim.get("place_result"):
        return False
    try:
        from tools.cache_store import set_places_details

        set_places_details(
            place_id,
            slim,
            status="ok",
            source=_SOURCE,
            ttl_days_ok=7,
        )
        logger.info(
            "[cache_places_details] upsert ok place_id=%s bytes≈%s (raw≈%s)",
            place_id,
            _payload_approx_bytes(slim),
            _payload_approx_bytes(raw),
        )
        return True
    except Exception as exc:
        logger.warning(
            "[cache_places_details] upsert fail place_id=%s %s: %s",
            place_id,
            type(exc).__name__,
            exc,
        )
        return False


def get_or_fetch_maps_place(place_id: str, *, force_refresh: bool = False) -> dict | None:
    """Cache-first google_maps_place. 1 rede call no miss.

    Retorno = payload rede (completo) no miss, ou slim do cache no hit.
    Consumidores (pico/reviews) só leem campos preservados no slim.
    """
    if not place_id:
        return None
    if not force_refresh:
        cached = get_cached_maps_place(place_id)
        if cached:
            return cached
    raw = fetch_maps_place_network(place_id)
    if raw:
        set_maps_place_cache(place_id, raw)
    return raw


def reviews_raw_from_maps_place(raw: dict | None) -> list[dict]:
    """Extrai review_results → shape compatível com google_maps_reviews (text/rating/user/date).

    Ordena rating asc (dores primeiro) — proxy de lowest_rating sem 2ª call.
    """
    pr = _place_result(raw)
    block = pr.get("review_results") if isinstance(pr.get("review_results"), dict) else {}
    items = block.get("reviews") if isinstance(block, dict) else None
    if not isinstance(items, list):
        return []
    out: list[dict] = []
    for rev in items:
        if not isinstance(rev, dict):
            continue
        texto = (rev.get("description") or rev.get("text") or rev.get("snippet") or "").strip()
        if not texto:
            continue
        try:
            rating = int(float(rev.get("rating") or 3))
        except (TypeError, ValueError):
            rating = 3
        user_raw = rev.get("user")
        user: dict[str, Any] = user_raw if isinstance(user_raw, dict) else {}
        out.append({
            "text": texto,
            "snippet": texto,
            "rating": rating,
            "user": {"name": (user.get("name") or "Anônimo")},
            "date": rev.get("date") or "",
            "review_id": rev.get("review_id"),
        })
    out.sort(key=lambda r: (r.get("rating") or 5, r.get("date") or ""))
    return out


def seed_reviews_cache_from_place(place_id: str, raw: dict | None) -> list[dict]:
    """Grava cache_reviews a partir do place (evita google_maps_reviews no warm)."""
    revs = reviews_raw_from_maps_place(raw)
    if not place_id or not revs:
        return revs
    try:
        from tools.cache_store import set_reviews

        set_reviews(place_id, revs, topics=[], source=_SOURCE)
    except Exception:
        pass
    return revs


def website_from_maps_place(raw: dict | None) -> str:
    pr = _place_result(raw)
    return (pr.get("website") or "").strip()
