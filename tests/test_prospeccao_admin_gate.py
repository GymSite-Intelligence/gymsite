"""Gate de admin nos endpoints de prospecção (P1.1 security review).

O módulo de prospecção é interno/admin-only, mas os endpoints /api/prospeccao/*
usavam só _require_authenticated (qualquer JWT). Estes testes travam o gate
require_admin: sem token → 401, autenticado não-admin → 403, admin → passa; e
garantem que TODOS os /api/prospeccao/* estão gateados.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

ADMIN_EMAIL = "marcelo.rosas@vectracargo.com.br"


def _req(auth: str | None = None) -> MagicMock:
    r = MagicMock()
    r.headers = {"authorization": auth} if auth else {}
    return r


def _mock_sb_user(email: str, role: str | None = None) -> MagicMock:
    user = MagicMock()
    user.email = email
    user.user_metadata = {"role": role} if role else {}
    user.id = "uid-1"
    sb = MagicMock()
    sb.auth.get_user.return_value = MagicMock(user=user)
    return sb


def test_sem_token_401():
    from fastapi import HTTPException

    from backend.routers.parceiros_admin import require_admin

    with pytest.raises(HTTPException) as exc:
        require_admin(_req())
    assert exc.value.status_code == 401


def test_autenticado_nao_admin_403(monkeypatch):
    from fastapi import HTTPException

    import backend.routers.parceiros_admin as pa

    monkeypatch.setenv("ADMIN_EMAILS", ADMIN_EMAIL)
    monkeypatch.setattr(pa, "_sb", lambda: _mock_sb_user("cliente@academia.com", role="user"))
    with pytest.raises(HTTPException) as exc:
        pa.require_admin(_req("Bearer tok"))
    assert exc.value.status_code == 403


def test_admin_por_email_passa(monkeypatch):
    import backend.routers.parceiros_admin as pa

    monkeypatch.setenv("ADMIN_EMAILS", ADMIN_EMAIL)
    monkeypatch.setattr(pa, "_sb", lambda: _mock_sb_user(ADMIN_EMAIL))
    res = pa.require_admin(_req("Bearer tok"))
    assert res["email"] == ADMIN_EMAIL


def test_admin_por_role_passa(monkeypatch):
    import backend.routers.parceiros_admin as pa

    monkeypatch.setenv("ADMIN_EMAILS", "")
    monkeypatch.setattr(pa, "_sb", lambda: _mock_sb_user("outro@x.com", role="admin"))
    res = pa.require_admin(_req("Bearer tok"))
    assert res["role"] == "admin"


def _route_depends_on(route, fn) -> bool:
    dep = getattr(route, "dependant", None)
    if dep is None:
        return False
    stack = list(dep.dependencies)
    while stack:
        d = stack.pop()
        if getattr(d, "call", None) is fn:
            return True
        stack.extend(d.dependencies)
    return False


def test_todos_endpoints_prospeccao_gateados():
    from api import app
    from backend.routers.parceiros_admin import require_admin

    faltando = [
        route.path
        for route in app.routes
        if getattr(route, "path", "").startswith("/api/prospeccao")
        and not _route_depends_on(route, require_admin)
    ]
    assert not faltando, f"endpoints de prospecção sem require_admin: {faltando}"
