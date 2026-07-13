"""
tools/cache_store.py — Cache no Supabase (service_role).

Uso recomendado:
- Somente backend (api.py / tools) com SUPABASE_SERVICE_ROLE_KEY.
- Não expor essas tabelas pro frontend (sem RLS por padrão).

Tabelas:
- cache_market_context
- cache_places_details
- cache_popular_times
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional
from tools.db_schema import tbl


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _dt_to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _get_client():
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        return None
    from supabase import create_client

    return create_client(url, key)


def _slug(s: str) -> str:
    # Mantém o mesmo comportamento do deep_research_tool (ASCII básico).
    import re

    s = s.strip().lower()
    s = re.sub(r"[áàâãä]", "a", s)
    s = re.sub(r"[éèêë]", "e", s)
    s = re.sub(r"[íìîï]", "i", s)
    s = re.sub(r"[óòôõö]", "o", s)
    s = re.sub(r"[úùûü]", "u", s)
    s = re.sub(r"[ç]", "c", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


MarketTier = Literal["interactions", "grounded", "briefing", "cache"]


@dataclass(frozen=True)
class CacheHit:
    hit: bool
    payload: Any | None


# -----------------------------------------------------------------------------
# cache_market_context
# -----------------------------------------------------------------------------


def get_market_context(
    cidade: str,
    bairro: str,
    uf: str | None = None,
) -> CacheHit:
    sb = _get_client()
    if not sb:
        return CacheHit(hit=False, payload=None)

    cidade_slug = _slug(cidade)
    bairro_slug = _slug(bairro)
    q = (
        tbl(sb, "cache_market_context")
        .select("*")
        .eq("cidade_slug", cidade_slug)
        .eq("bairro_slug", bairro_slug)
    )
    if uf:
        q = q.eq("uf", uf)
    else:
        q = q.is_("uf", None)

    q = q.gt("expires_at", _dt_to_iso(_utcnow())).limit(1)
    res = q.execute()
    row = (res.data or [None])[0]
    if not row:
        return CacheHit(hit=False, payload=None)

    try:
        tbl(sb, "cache_market_context").update(
            {"last_hit_at": _dt_to_iso(_utcnow()), "hit_count": int(row.get("hit_count") or 0) + 1}
        ).eq("id", row["id"]).execute()
    except Exception:
        pass

    return CacheHit(hit=True, payload=row)


def set_market_context(
    cidade: str,
    bairro: str,
    conteudo_md: str,
    *,
    uf: str | None = None,
    tier: MarketTier = "cache",
    ttl_days: int = 7,
    fontes: Optional[list[str]] = None,
    created_by_relatorio_id: str | None = None,
) -> None:
    sb = _get_client()
    if not sb:
        return

    now = _utcnow()
    row = {
        "cidade": cidade,
        "uf": uf,
        "bairro": bairro,
        "cidade_slug": _slug(cidade),
        "bairro_slug": _slug(bairro),
        "conteudo_md": conteudo_md,
        "tier": tier,
        "fontes": fontes or [],
        "cached_at": _dt_to_iso(now),
        "expires_at": _dt_to_iso(now + timedelta(days=ttl_days)),
        "last_hit_at": None,
        "hit_count": 0,
        "created_by_relatorio_id": created_by_relatorio_id,
    }

    # Upsert pela unique key (cidade_slug, uf, bairro_slug)
    tbl(sb, "cache_market_context").upsert(
        row,
        on_conflict="cidade_slug,uf,bairro_slug",
    ).execute()


# -----------------------------------------------------------------------------
# cache_places_details
# -----------------------------------------------------------------------------


def get_places_details(place_id: str) -> CacheHit:
    sb = _get_client()
    if not sb:
        return CacheHit(hit=False, payload=None)

    res = (
        tbl(sb, "cache_places_details")
        .select("*")
        .eq("place_id", place_id)
        .gt("expires_at", _dt_to_iso(_utcnow()))
        .limit(1)
        .execute()
    )
    row = (res.data or [None])[0]
    if not row:
        return CacheHit(hit=False, payload=None)

    try:
        tbl(sb, "cache_places_details").update(
            {"last_hit_at": _dt_to_iso(_utcnow()), "hit_count": int(row.get("hit_count") or 0) + 1}
        ).eq("place_id", place_id).execute()
    except Exception:
        pass

    return CacheHit(hit=True, payload=row)


def set_places_details(
    place_id: str,
    payload: dict,
    *,
    status: str = "ok",
    source: str | None = "places_new",
    ttl_days_ok: int = 7,
    ttl_days_err: int = 1,
) -> None:
    sb = _get_client()
    if not sb:
        return

    now = _utcnow()
    ttl_days = ttl_days_ok if status == "ok" else ttl_days_err
    row = {
        "place_id": place_id,
        "payload": payload,
        "status": status,
        "source": source,
        "cached_at": _dt_to_iso(now),
        "expires_at": _dt_to_iso(now + timedelta(days=ttl_days)),
        "last_hit_at": None,
        "hit_count": 0,
    }
    tbl(sb, "cache_places_details").upsert(row, on_conflict="place_id").execute()


def get_geocode(endereco_norm: str) -> CacheHit:
    """Geocode cacheado (endereco_norm → lat/lng). Geocode é estável → TTL 90d."""
    sb = _get_client()
    if not sb:
        return CacheHit(hit=False, payload=None)
    res = (
        tbl(sb, "cache_geocode").select("*")
        .eq("endereco_norm", endereco_norm)
        .gt("expires_at", _dt_to_iso(_utcnow())).limit(1).execute()
    )
    row = (res.data or [None])[0]
    if not row:
        return CacheHit(hit=False, payload=None)
    try:
        tbl(sb, "cache_geocode").update(
            {"last_hit_at": _dt_to_iso(_utcnow()), "hit_count": int(row.get("hit_count") or 0) + 1}
        ).eq("endereco_norm", endereco_norm).execute()
    except Exception:
        pass
    return CacheHit(hit=True, payload=row)


def set_geocode(endereco_norm: str, lat, lng, payload: dict, *,
                source: str = "google", ttl_days: int = 90) -> None:
    sb = _get_client()
    if not sb:
        return
    now = _utcnow()
    tbl(sb, "cache_geocode").upsert({
        "endereco_norm": endereco_norm, "lat": lat, "lng": lng, "payload": payload,
        "source": source, "cached_at": _dt_to_iso(now),
        "expires_at": _dt_to_iso(now + timedelta(days=ttl_days)),
        "last_hit_at": None, "hit_count": 0,
    }, on_conflict="endereco_norm").execute()


def get_reviews(place_id: str) -> CacheHit:
    """Reviews crus do concorrente (place_id). Mata o 2× (2 funções, mesmo place_id)
    + determinístico cross-run. TTL 7d."""
    sb = _get_client()
    if not sb or not place_id:
        return CacheHit(hit=False, payload=None)
    res = (tbl(sb, "cache_reviews").select("*").eq("place_id", place_id)
           .gt("expires_at", _dt_to_iso(_utcnow())).limit(1).execute())
    row = (res.data or [None])[0]
    if not row:
        return CacheHit(hit=False, payload=None)
    try:
        tbl(sb, "cache_reviews").update({"hit_count": int(row.get("hit_count") or 0) + 1}).eq(
            "place_id", place_id).execute()
    except Exception:
        pass
    return CacheHit(hit=True, payload=row)


def set_reviews(place_id: str, reviews: list, *, topics: list | None = None, source: str = "searchapi", ttl_days: int = 7) -> None:
    sb = _get_client()
    if not sb or not place_id:
        return
    now = _utcnow()
    payload: dict | list = {"reviews": reviews, "topics": topics or []} if topics is not None else reviews
    row: dict = {
        "place_id": place_id, "reviews": payload, "source": source,
        "cached_at": _dt_to_iso(now),
        "expires_at": _dt_to_iso(now + timedelta(days=ttl_days)), "hit_count": 0,
    }
    tbl(sb, "cache_reviews").upsert(row, on_conflict="place_id").execute()


# -----------------------------------------------------------------------------
# cache_popular_times
# -----------------------------------------------------------------------------


def get_popular_times(place_id: str) -> CacheHit:
    sb = _get_client()
    if not sb:
        return CacheHit(hit=False, payload=None)

    res = (
        tbl(sb, "cache_popular_times")
        .select("*")
        .eq("place_id", place_id)
        .gt("expires_at", _dt_to_iso(_utcnow()))
        .limit(1)
        .execute()
    )
    row = (res.data or [None])[0]
    if not row:
        return CacheHit(hit=False, payload=None)

    try:
        tbl(sb, "cache_popular_times").update(
            {"last_hit_at": _dt_to_iso(_utcnow()), "hit_count": int(row.get("hit_count") or 0) + 1}
        ).eq("place_id", place_id).execute()
    except Exception:
        pass

    return CacheHit(hit=True, payload=row)


def set_popular_times(
    place_id: str,
    payload: dict | None,
    *,
    status: str = "ok",
    ttl_days_ok: int = 7,
    ttl_days_sem_dados: int = 1,
) -> None:
    sb = _get_client()
    if not sb:
        return

    now = _utcnow()
    ttl_days = ttl_days_ok if status == "ok" else ttl_days_sem_dados
    row = {
        "place_id": place_id,
        "payload": payload,
        "status": status,
        "cached_at": _dt_to_iso(now),
        "expires_at": _dt_to_iso(now + timedelta(days=ttl_days)),
        "last_hit_at": None,
        "hit_count": 0,
    }
    tbl(sb, "cache_popular_times").upsert(row, on_conflict="place_id").execute()

