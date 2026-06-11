"""Testes CKAN client (mock, sem rede)."""
from __future__ import annotations

import pytest

from tools.ckan_client import CkanApiError, ckan_action, package_search, search_datasets_for_city


def _mock_client(resp):
    """Client fake cobrindo GET (ações de leitura) e POST (demais)."""
    handler = type("H", (), {
        "get": lambda *a, **k: resp,
        "post": lambda *a, **k: resp,
    })()
    return type("C", (), {
        "__enter__": lambda s: handler,
        "__exit__": lambda *a: None,
    })()


def test_ckan_action_success(monkeypatch):
    class Resp:
        status_code = 200

        def json(self):
            return {"success": True, "result": {"count": 0, "results": []}}

    monkeypatch.setattr("tools.ckan_client.httpx.Client", lambda **kw: _mock_client(Resp()))
    r = ckan_action("status_show", portal_base="https://example.com")
    assert r == {"count": 0, "results": []}


def test_ckan_action_failure(monkeypatch):
    class Resp:
        status_code = 200

        def json(self):
            return {"success": False, "error": {"message": "not found"}}

    monkeypatch.setattr("tools.ckan_client.httpx.Client", lambda **kw: _mock_client(Resp()))
    with pytest.raises(CkanApiError):
        ckan_action("package_show", {"id": "x"}, portal_base="https://example.com")


def test_search_datasets_for_city_dedup(monkeypatch):
    def fake_search(q, **kwargs):
        return {"results": [{"id": "a", "name": "a", "title": "T", "organization": {}}]}

    monkeypatch.setattr("tools.ckan_client.package_search", fake_search)
    out = search_datasets_for_city("Fortaleza", "CE")
    assert len(out) >= 1
    assert out[0]["id"] == "a"
