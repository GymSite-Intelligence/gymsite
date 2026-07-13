"""Cache Supabase para análises de fluxo pedestre (GeoJSON + stats)."""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

TTL_DAYS = 90


def _cache_key(lat: float, lng: float, radius_m: int, network_type: str) -> str:
    raw = f"{lat:.5f}|{lng:.5f}|{radius_m}|{network_type}|v1"
    return hashlib.sha256(raw.encode()).hexdigest()


def _supabase():
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_KEY")
    )
    url = os.environ.get("SUPABASE_URL")
    if not url or not key:
        return None
    from tools.supabase_client import load_create_client
    return load_create_client()(url, key)


def get_cached_flow(lat: float, lng: float, radius_m: int, network_type: str = "walk") -> dict | None:
    sb = _supabase()
    if sb is None:
        return None
    key = _cache_key(lat, lng, radius_m, network_type)
    try:
        res = (
            sb.table("spatial_flow_cache")
            .select("payload,expires_at")
            .eq("cache_key", key)
            .maybe_single()
            .execute()
        )
        row = res.data
        if not row:
            return None
        expires = row.get("expires_at")
        if expires:
            exp_dt = datetime.fromisoformat(str(expires).replace("Z", "+00:00"))
            if exp_dt < datetime.now(timezone.utc):
                return None
        payload = row.get("payload")
        return payload if isinstance(payload, dict) else None
    except Exception as exc:
        logger.warning("spatial_flow_cache get falhou: %s", exc)
        return None


def set_cached_flow(
    lat: float,
    lng: float,
    radius_m: int,
    payload: dict[str, Any],
    network_type: str = "walk",
) -> None:
    sb = _supabase()
    if sb is None:
        return
    key = _cache_key(lat, lng, radius_m, network_type)
    expires = datetime.now(timezone.utc) + timedelta(days=TTL_DAYS)
    row = {
        "cache_key": key,
        "lat": lat,
        "lng": lng,
        "radius_m": radius_m,
        "network_type": network_type,
        "payload": payload,
        "expires_at": expires.isoformat(),
    }
    try:
        sb.table("spatial_flow_cache").upsert(row, on_conflict="cache_key").execute()
    except Exception as exc:
        logger.warning("spatial_flow_cache set falhou: %s", exc)
