# tools/redis_rate_limit.py — Rate Limiting com Redis (Token Bucket)
"""
Middleware FastAPI que limita requisições por IP e por user JWT.
Estratégia: Token Bucket — permite bursts controlados.
"""
from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from tools.redis_client import get_redis

# Configurações (requests por minuto)
DEFAULT_RPM = 60          # IP anônimo
AUTH_RPM = 120            # Usuário autenticado
PDF_RPM = 10              # Endpoint de PDF (mais restritivo)
HEALTH_RPM = 30           # Health check (liberal)

WINDOW_SEC = 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting via Redis Token Bucket."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Preflight CORS — não consome bucket; CORSMiddleware responde
        if request.method == "OPTIONS":
            return await call_next(request)

        try:
            r = await get_redis()
        except Exception:
            return await call_next(request)

        path = request.url.path
        client_id = self._client_id(request)
        limit = self._limit_for_path(path, request)
        key = f"ratelimit:{client_id}:{path.split('/')[1]}"

        try:
            allowed = await self._check(r, key, limit)
            if not allowed:
                return Response(
                    content='{"detail":"Rate limit exceeded. Try again later."}',
                    status_code=429,
                    media_type="application/json",
                    headers={"Retry-After": str(WINDOW_SEC)},
                )

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(limit)
            remaining = await self._remaining(r, key, limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            return response
        except Exception:
            # Redis falhou — deixa passar
            return await call_next(request)

    @staticmethod
    def _client_id(request: Request) -> str:
        """Identifica cliente por IP ou user_id do JWT."""
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            # Simplificado: usa hash do token como ID
            token = auth[7:]
            return f"u:{hash(token) & 0xFFFFFFFF}"
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        return f"ip:{request.client.host if request.client else 'unknown'}"

    @staticmethod
    def _limit_for_path(path: str, request: Request) -> int:
        if path == "/health":
            return HEALTH_RPM
        if path.endswith("/pdf"):
            return PDF_RPM
        if request.headers.get("authorization", "").lower().startswith("bearer "):
            return AUTH_RPM
        return DEFAULT_RPM

    @staticmethod
    async def _check(r, key: str, limit: int) -> bool:
        """Token bucket: adiciona tokens ao longo do tempo e consome 1."""
        now = time.time()
        pipe = r.pipeline()
        pipe.hmget(key, ["tokens", "last"])
        result = await pipe.execute()
        tokens_str, last_str = result[0]

        tokens = float(tokens_str) if tokens_str else float(limit)
        last = float(last_str) if last_str else now

        # Recarrega tokens proporcional ao tempo decorrido
        elapsed = now - last
        tokens = min(limit, tokens + elapsed * (limit / WINDOW_SEC))

        if tokens < 1:
            # Salva estado atualizado (sem consumir)
            await r.hset(key, mapping={"tokens": str(tokens), "last": str(now)})
            await r.expire(key, WINDOW_SEC * 2)
            return False

        tokens -= 1
        await r.hset(key, mapping={"tokens": str(tokens), "last": str(now)})
        await r.expire(key, WINDOW_SEC * 2)
        return True

    @staticmethod
    async def _remaining(r, key: str, limit: int) -> int:
        tokens = await r.hget(key, "tokens")
        return max(0, int(float(tokens))) if tokens else limit
