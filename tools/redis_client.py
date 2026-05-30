# tools/redis_client.py — Cliente Redis async singleton
"""
Conexão Redis shared pra rate limit, cache, queue e pub/sub.
Auto-reconnect + health check.
"""
from __future__ import annotations

import os
from typing import Any

import redis.asyncio as redis

_redis_pool: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """Retorna cliente Redis (singleton)."""
    global _redis_pool
    if _redis_pool is None:
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_pool = redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=10.0,
            socket_timeout=60.0,
        )
    return _redis_pool


async def redis_health() -> dict[str, Any]:
    """Health check rápido do Redis."""
    try:
        r = await get_redis()
        info = await r.ping()
        return {"status": "ok", "ping": info}
    except Exception as e:
        return {"status": "error", "error": str(e)}
