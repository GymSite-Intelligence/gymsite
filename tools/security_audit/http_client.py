from __future__ import annotations

import asyncio
import time
from typing import Any
from urllib.parse import urlencode, urljoin, urlparse, parse_qs, urlunparse

import httpx

from tools.security_audit.config import AuditConfig
from tools.security_audit.models import HttpExchange


class RateLimitedClient:
    """HTTP client with internal rate limiting and proxy support."""

    def __init__(self, base_url: str, config: AuditConfig) -> None:
        self.base_url = base_url.rstrip("/")
        self.config = config
        self._min_interval = 1.0 / max(config.internal_rate_limit_rps, 0.1)
        self._last_request = 0.0
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=config.timeout_sec,
            verify=config.verify_ssl,
            proxy=config.proxy,
            follow_redirects=False,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _throttle(self) -> None:
        now = time.monotonic()
        wait = self._min_interval - (now - self._last_request)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_request = time.monotonic()

    async def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        content: str | None = None,
    ) -> HttpExchange:
        await self._throttle()
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        hdrs = headers or {}
        started = time.perf_counter()
        try:
            resp = await self._client.request(
                method,
                url,
                headers=hdrs,
                params=params,
                json=json_body,
                content=content,
            )
            elapsed_ms = (time.perf_counter() - started) * 1000
            body = resp.text[:8000] if resp.text else ""
            return HttpExchange(
                method=method,
                url=str(resp.request.url),
                request_headers=dict(resp.request.headers),
                request_body=content or (str(json_body) if json_body else None),
                status_code=resp.status_code,
                response_headers={k.lower(): v for k, v in resp.headers.items()},
                response_body=body,
                elapsed_ms=elapsed_ms,
            )
        except httpx.HTTPError as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000
            return HttpExchange(
                method=method,
                url=url,
                request_headers=hdrs,
                request_body=content or (str(json_body) if json_body else None),
                status_code=None,
                response_body=str(exc),
                elapsed_ms=elapsed_ms,
            )

    async def get(self, path: str, **kwargs: Any) -> HttpExchange:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> HttpExchange:
        return await self.request("POST", path, **kwargs)

    async def options(self, path: str, **kwargs: Any) -> HttpExchange:
        return await self.request("OPTIONS", path, **kwargs)


def token_in_url(url: str) -> bool:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    for key in qs:
        if any(t in key.lower() for t in ("token", "jwt", "access", "auth")):
            return True
    return False


def join_url(base: str, path: str) -> str:
    return urljoin(base.rstrip("/") + "/", path.lstrip("/"))
