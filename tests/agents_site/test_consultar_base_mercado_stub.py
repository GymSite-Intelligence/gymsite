"""Vertex RAG off → stub limpo; consultar_base_mercado não vaza billing."""
from __future__ import annotations

import os
from unittest.mock import patch

from tools.discovery_engine_tools import buscar_conhecimento, vertex_rag_enabled


def test_vertex_rag_default_off():
    with patch.dict(os.environ, {"VERTEX_RAG_ENABLED": ""}, clear=False):
        assert vertex_rag_enabled() is False


def test_buscar_conhecimento_stub_quando_off():
    with patch.dict(os.environ, {"VERTEX_RAG_ENABLED": "0"}, clear=False):
        r = buscar_conhecimento("tendência academias")
    assert r["n_docs"] == 0
    assert r["status"] == "deprecated"
    assert "aviso_usuario" in r
    assert "faturamento" not in (r.get("aviso_usuario") or "").lower()
    assert "billing" not in (r.get("erro") or "").lower()


def test_consultar_base_mercado_stub_sem_eros():
    with patch.dict(
        os.environ,
        {"VERTEX_RAG_ENABLED": "0", "EROS_GROUP_ID_MERCADO": ""},
        clear=False,
    ):
        from agents_site.tools import consultar_base_mercado

        r = consultar_base_mercado("por que saturação baixa")
    assert r["n_docs"] == 0
    assert r.get("status") in ("vazio", "deprecated", "indisponivel")
    assert r.get("aviso_usuario")
    raw = str(r).lower()
    assert "billing" not in raw
    assert "vertex" not in (r.get("fonte") or "").lower()
    assert "faturamento" not in raw


def test_sanitize_billing_quando_vertex_on():
    with patch.dict(os.environ, {"VERTEX_RAG_ENABLED": "1"}, clear=False):
        with patch(
            "google.cloud.discoveryengine_v1.SearchServiceClient",
            side_effect=RuntimeError(
                "PERMISSION_DENIED: billing account has not been used / faturamento"
            ),
        ):
            r = buscar_conhecimento("x")
    assert r["n_docs"] == 0
    assert r.get("status") == "indisponivel"
    assert "vertex_billing_off" in (r.get("erro") or "")
    assert "aviso_usuario" in r
