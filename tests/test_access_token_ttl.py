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


@pytest.mark.asyncio
async def test_status_analise_maybe_single_none_vira_404(monkeypatch):
    """Coluna expires ausente + 0 rows: execute() pode ser None — não pode 500."""
    from backend.routers import site_agent as sa
    from fastapi import HTTPException
    from starlette.requests import Request

    class _Q:
        def select(self, *_a, **_k):
            return self

        def eq(self, *_a, **_k):
            return self

        def maybe_single(self):
            return self

        def execute(self):
            raise RuntimeError("column missing")

    class _Q2(_Q):
        def execute(self):
            return None

    calls = {"n": 0}

    def fake_tbl(*_a, **_k):
        calls["n"] += 1
        return _Q() if calls["n"] == 1 else _Q2()

    monkeypatch.setattr(sa, "_sb", lambda: object())
    monkeypatch.setattr(sa, "tbl", fake_tbl)

    scope = {"type": "http", "method": "GET", "path": "/", "headers": [], "query_string": b""}
    req = Request(scope)
    with pytest.raises(HTTPException) as ei:
        await sa.status_analise("rel-1", req, x_access_token="tok-x")
    assert ei.value.status_code == 404


@pytest.mark.asyncio
async def test_status_analise_pronto_invalida_token_oneshot(monkeypatch):
    """1ª resposta pronto invalida token; 2ª poll com mesmo token → 404."""
    from backend.routers import site_agent as sa
    from fastapi import HTTPException
    from starlette.requests import Request

    token = "cap-token-uuid"
    rel_id = "rel-done-1"
    future = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    row_done = {
        "id": rel_id,
        "status": "done",
        "access_token": token,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "access_token_expires_at": future,
    }
    invalidated = {"called": False}

    class _Exec:
        def __init__(self, data):
            self.data = data

    class _Q:
        def __init__(self, table: str):
            self._table = table
            self._select = "*"

        def select(self, cols, **_k):
            self._select = cols
            return self

        def eq(self, *_a, **_k):
            return self

        def order(self, *_a, **_k):
            return self

        def limit(self, *_a, **_k):
            return self

        def maybe_single(self):
            return self

        def update(self, payload):
            self._update_payload = payload
            return self

        def execute(self):
            if self._table == "relatorios" and getattr(self, "_update_payload", None) is not None:
                invalidated["called"] = True
                row_done["access_token"] = None
                return _Exec(None)
            if self._table == "relatorios" and "bairro" in str(self._select):
                return _Exec({"bairro": "Centro"})
            if self._table == "relatorios":
                if row_done.get("access_token") is None:
                    return None
                return _Exec(dict(row_done))
            if self._table == "relatorio_outputs":
                return _Exec({"veredito": "OK", "resumo_executivo": "Resumo"})
            if self._table == "competidores":
                return _Exec([])
            return _Exec(None)

    monkeypatch.setattr(sa, "_sb", lambda: object())
    monkeypatch.setattr(sa, "tbl", lambda _sb, name: _Q(name))

    scope = {"type": "http", "method": "GET", "path": "/", "headers": [], "query_string": b""}
    req = Request(scope)

    out = await sa.status_analise(rel_id, req, x_access_token=token)
    assert out["status"] == "pronto"
    assert invalidated["called"] is True

    with pytest.raises(HTTPException) as ei:
        await sa.status_analise(rel_id, req, x_access_token=token)
    assert ei.value.status_code == 404
