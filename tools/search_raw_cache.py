"""Cache imutável de payloads SearchAPI (RAW) — base de replay e economia de API.

Chave: (engine, params_hash). Ver docs/A9_SEARCHAPI_INGESTION.md.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from tools.db_schema import tbl

logger = logging.getLogger(__name__)

DEFAULT_TTL_DAYS: dict[str, int] = {
    "google_maps": 14,
    "google_maps_reviews": 7,
    "instagram_profile": 3,
    "google_light": 1,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _dt_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _supabase():
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_KEY")
        or ""
    ).strip()
    if not url or not key:
        return None
    from supabase import create_client

    return create_client(url, key)


def params_hash(engine: str, params: dict[str, Any]) -> str:
    canonical = {"engine": engine, **params}
    blob = json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def get_search_raw(engine: str, params: dict[str, Any]) -> dict[str, Any] | None:
    sb = _supabase()
    if sb is None:
        return None
    ph = params_hash(engine, params)
    try:
        res = (
            tbl(sb, "search_raw")
            .select("payload,search_id,fetched_at,expires_at")
            .eq("engine", engine)
            .eq("params_hash", ph)
            .gt("expires_at", _dt_iso(_utcnow()))
            .limit(1)
            .execute()
        )
        row = (res.data or [None])[0]
        if not row:
            return None
        payload = row.get("payload")
        if isinstance(payload, dict):
            payload.setdefault("_cache", {})
            if isinstance(payload["_cache"], dict):
                payload["_cache"].update(
                    {
                        "hit": True,
                        "search_id": row.get("search_id"),
                        "fetched_at": row.get("fetched_at"),
                    }
                )
        return payload if isinstance(payload, dict) else None
    except Exception as exc:
        logger.warning("search_raw get falhou: %s", exc)
        return None


def set_search_raw(
    engine: str,
    params: dict[str, Any],
    payload: dict[str, Any],
    *,
    search_id: str | None = None,
    relatorio_id: str | None = None,
    ttl_days: int | None = None,
) -> None:
    sb = _supabase()
    if sb is None or not isinstance(payload, dict):
        return
    ph = params_hash(engine, params)
    meta = payload.get("search_metadata") if isinstance(payload.get("search_metadata"), dict) else {}
    sid = (search_id or meta.get("id") or "").strip() or f"local_{ph[:16]}"
    ttl = ttl_days if ttl_days is not None else DEFAULT_TTL_DAYS.get(engine, 7)
    now = _utcnow()
    row = {
        "search_id": sid,
        "engine": engine,
        "params_hash": ph,
        "params": params,
        "payload": payload,
        "relatorio_id": relatorio_id,
        "fetched_at": _dt_iso(now),
        "expires_at": _dt_iso(now + timedelta(days=ttl)),
    }
    try:
        tbl(sb, "search_raw").upsert(row, on_conflict="engine,params_hash").execute()
    except Exception as exc:
        logger.warning("search_raw set falhou: %s", exc)
