"""P0 access_token: header X-Access-Token + TTL (created_at / expires_at)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


def test_access_token_expirado_via_expires_at():
    from backend.routers import site_agent as sa

    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    assert sa._access_token_expirado({"access_token_expires_at": past}) is True
    assert sa._access_token_expirado({"access_token_expires_at": future}) is False


def test_access_token_expirado_via_created_at_ttl(monkeypatch):
    from backend.routers import site_agent as sa

    monkeypatch.setattr(sa, "_TOKEN_TTL_HOURS", 48)
    old = (datetime.now(timezone.utc) - timedelta(hours=49)).isoformat()
    recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    assert sa._access_token_expirado({"created_at": old}) is True
    assert sa._access_token_expirado({"created_at": recent}) is False


def test_access_token_sem_ancora_fail_closed():
    from backend.routers import site_agent as sa

    assert sa._access_token_expirado({}) is True
    assert sa._access_token_expirado({"access_token": "x"}) is True


@pytest.mark.asyncio
async def test_status_analise_exige_header(monkeypatch):
    from backend.routers import site_agent as sa
    from fastapi import HTTPException
    from starlette.requests import Request

    scope = {"type": "http", "method": "GET", "path": "/", "headers": [], "query_string": b""}
    req = Request(scope)

    with pytest.raises(HTTPException) as ei:
        await sa.status_analise("rel-1", req, x_access_token=None)
    assert ei.value.status_code == 404
