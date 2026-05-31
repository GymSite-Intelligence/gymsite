# tools/redis_cache.py — Response Cache com Redis
"""
Cacheia respostas GET no Redis (JSON / bytes) com TTL configurável.
Invalidação automática por path pattern.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from tools.redis_client import get_redis

# TTL por padrão de rota (segundos)
CACHE_TTL: dict[str, int] = {
    "/health": 60,
    "/api/metrics": 15,
    "/api/relatorios": 300,
    "/api/relatorios/{id}/pdf": 3600,
    "/api/relatorios/{id}/custos-api": 300,
    "/api/relatorios/{id}/status": 30,
    "/api/custos": 900,
    "/api/canais/status": 60,
    "/api/prospeccao/oportunidades": 300,
}

MAX_BODY_SIZE = 1024 * 1024  # 1 MB — não cacheia respostas gigantes


class RedisCacheMiddleware(BaseHTTPMiddleware):
    """Cacheia respostas GET no Redis."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method != "GET":
            return await call_next(request)

        ttl = self._ttl_for_path(request.url.path)
        if ttl is None:
            return await call_next(request)

        try:
            r = await get_redis()
        except Exception:
            return await call_next(request)

        cache_key = self._make_key(request)

        try:
            # Tentar hit
            cached = await r.get(cache_key)
            if cached:
                data = json.loads(cached)
                response = Response(
                    content=data["body"].encode() if isinstance(data["body"], str) else data["body"],
                    status_code=data["status"],
                    media_type=data.get("media_type", "application/json"),
                    headers={**data.get("headers", {}), "X-Cache": "HIT"},
                )
                return response
        except Exception:
            pass  # Redis falhou — continua como miss

        # Miss — executa e cacheia
        response = await call_next(request)

        if response.status_code != 200:
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        if len(body) > MAX_BODY_SIZE:
            return Response(content=body, status_code=response.status_code, headers=dict(response.headers))

        try:
            cache_data = {
                "body": body.decode("utf-8", errors="replace"),
                "status": response.status_code,
                "media_type": response.media_type,
                "headers": dict(response.headers),
            }
            await r.setex(cache_key, ttl, json.dumps(cache_data))
            return Response(
                content=body,
                status_code=response.status_code,
                media_type=response.media_type,
                headers={**dict(response.headers), "X-Cache": "MISS"},
            )
        except Exception:
            return Response(
                content=body,
                status_code=response.status_code,
                media_type=response.media_type,
                headers=dict(response.headers),
            )

    @staticmethod
    def _ttl_for_path(path: str) -> int | None:
        for pattern, ttl in CACHE_TTL.items():
            regex = pattern.replace("{id}", r"[^/]+")
            import re
            if re.match(f"^{regex}$", path):
                return ttl
        return None

    @staticmethod
    def _make_key(request: Request) -> str:
        """Chave única incluindo path + query + accept-encoding."""
        parts = [request.method, request.url.path, request.url.query]
        token = request.headers.get("authorization", "")
        if token:
            parts.append("auth")
        raw = "|".join(parts)
        return f"cache:{hashlib.sha256(raw.encode()).hexdigest()[:32]}"


async def invalidate_cache_pattern(path_pattern: str) -> int:
    """Invalida cache por pattern (ex: '/api/relatorios/*')."""
    try:
        r = await get_redis()
        keys = []
        async for key in r.scan_iter(match="cache:*"):
            keys.append(key)
        if keys:
            await r.delete(*keys)
        return len(keys)
    except Exception:
        return 0
