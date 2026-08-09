# tools/redis_client.py — Cliente Redis async singleton
"""
Conexão Redis shared pra rate limit, cache, queue e pub/sub.
Auto-reconnect + health check.
"""
from __future__ import annotations

import os
from typing import Any

import redis as redis_sync
import redis.asyncio as redis

_redis_pool: redis.Redis | None = None
_redis_sync_client: redis_sync.Redis | None = None


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


async def get_redis() -> redis.Redis:
    """Retorna cliente Redis (singleton)."""
    global _redis_pool
    if _redis_pool is None:
        # socket_timeout must exceed longest blocking command (BRPOP ~30s in redis_queue)
        _redis_pool = redis.from_url(
            _redis_url(),
            decode_responses=True,
            socket_connect_timeout=3.0,
            socket_timeout=35.0,
            max_connections=10,
        )
    return _redis_pool


def get_redis_sync() -> redis_sync.Redis:
    """Cliente sync curto — override LLM / leituras no path ADK (não BRPOP)."""
    global _redis_sync_client
    if _redis_sync_client is None:
        _redis_sync_client = redis_sync.from_url(
            _redis_url(),
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
            max_connections=4,
        )
    return _redis_sync_client


async def redis_health() -> dict[str, Any]:
    """Health check rápido do Redis."""
    try:
        r = await get_redis()
        info = await r.ping()
        return {"status": "ok", "ping": info}
    except Exception as e:
        return {"status": "error", "error": str(e)}
