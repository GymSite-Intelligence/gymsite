"""Rota LLM site/consultor + mensagens de falha visíveis."""
from __future__ import annotations

import os

import pytest

from agents_site.llm_route import (
    is_vertex_dunning,
    mensagem_falha_turno,
    site_chat_developer_api,
)


def test_dunning_detecta_lightning():
    exc = Exception(
        "403 PERMISSION_DENIED. Lightning dunning decision is deny for project: "
        "projects/258980081869"
    )
    assert is_vertex_dunning(exc) is True
    msg = mensagem_falha_turno(exc)
    assert "cobrança" in msg.lower() or "bloqueado" in msg.lower()


def test_mensagem_generica_sem_dunning():
    msg = mensagem_falha_turno(RuntimeError("boom interno"))
    assert "reformular" in msg.lower() or "instantes" in msg.lower()


def test_site_chat_developer_api_ativa_e_restaura(monkeypatch):
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("GYMSITE_GEMINI_FALLBACK_KEY", "AIzaSyTestFallbackKey000")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("SITE_CHAT_USE_DEVELOPER_API", "1")

    class _Dummy:
        model = type("M", (), {})()
        sub_agents = []

    dummy = _Dummy()
    with site_chat_developer_api(dummy) as ativo:
        assert ativo is True
        assert os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") == "false"
        assert os.environ.get("GEMINI_API_KEY") == "AIzaSyTestFallbackKey000"

    assert os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") == "true"
    assert "GEMINI_API_KEY" not in os.environ


def test_site_chat_developer_api_off_sem_key(monkeypatch):
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.delenv("GYMSITE_GEMINI_FALLBACK_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    class _Dummy:
        model = None
        sub_agents = []

    with site_chat_developer_api(_Dummy()) as ativo:
        assert ativo is False
