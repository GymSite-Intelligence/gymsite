"""P2.2 + P3.2 (SECURITY_REVIEW.md): /docs fechado por default + security headers."""
from __future__ import annotations

from fastapi.testclient import TestClient


def _client() -> TestClient:
    from api import app

    return TestClient(app)


def test_docs_fechado_por_default():
    """Sem EXPOSE_API_DOCS, /docs, /redoc e /openapi.json NÃO servem conteúdo (não 200).
    O status pode ser 404 ou 405 (há um catch-all OPTIONS /{path:path}); o que importa
    é que a superfície da API não vaza — nenhum retorna 200 com o schema/UI."""
    c = _client()
    assert c.get("/docs").status_code != 200
    assert c.get("/openapi.json").status_code != 200
    assert c.get("/redoc").status_code != 200


def test_security_headers_presentes():
    """Toda resposta carrega os headers de segurança básicos."""
    c = _client()
    r = c.get("/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert "max-age=" in (r.headers.get("Strict-Transport-Security") or "")
    assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
