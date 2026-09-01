"""PIPELINE_LLM_PROVIDER resolve — nvidia fora do Vertex billing."""
from __future__ import annotations

import os

from tools.pipeline_model import (
    DEFAULT_NVIDIA_MODEL,
    friendly_pipeline_429_message,
    gemini_side_tools_ok,
    pipeline_llm_provider,
    pipeline_ollama_fallback_enabled,
    resolve_pipeline_model,
    using_pipeline_litellm,
    using_pipeline_nvidia,
)


def test_default_nvidia_model_not_eol_llama31_8b():
    """Hosted NIM retired meta/llama-3.1-8b-instruct 2026-08-26 (HTTP 410)."""
    assert DEFAULT_NVIDIA_MODEL == "nvidia/nemotron-3-nano-30b-a3b"
    assert "llama-3.1-8b-instruct" not in DEFAULT_NVIDIA_MODEL


def test_explicit_nvidia(monkeypatch):
    monkeypatch.setenv("PIPELINE_LLM_PROVIDER", "nvidia")
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")
    monkeypatch.delenv("NVIDIA_MODEL", raising=False)
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    assert pipeline_llm_provider() == "nvidia"
    assert using_pipeline_nvidia() is True
    m = resolve_pipeline_model("gemini-3.6-flash")
    assert DEFAULT_NVIDIA_MODEL in getattr(m, "model", "")


def test_explicit_vertex(monkeypatch):
    monkeypatch.setenv("PIPELINE_LLM_PROVIDER", "vertex")
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    assert pipeline_llm_provider() == "vertex"
    assert resolve_pipeline_model("gemini-3.6-flash") == "gemini-3.6-flash"


def test_alias_legacy_25_to_36(monkeypatch):
    monkeypatch.setenv("PIPELINE_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "false")
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    assert resolve_pipeline_model("gemini-2.5-flash") == "gemini-3.6-flash"
    assert resolve_pipeline_model("gemini-flash-3.6") == "gemini-3.6-flash"


def test_auto_nvidia_when_vertex_off(monkeypatch):
    monkeypatch.delenv("PIPELINE_LLM_PROVIDER", raising=False)
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "false")
    monkeypatch.setenv("LLM_PROVIDER", "nvidia")
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")
    assert pipeline_llm_provider() == "nvidia"


def test_auto_vertex_when_flag_on(monkeypatch):
    monkeypatch.delenv("PIPELINE_LLM_PROVIDER", raising=False)
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    monkeypatch.setenv("LLM_PROVIDER", "nvidia")
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")
    assert pipeline_llm_provider() == "vertex"


def test_429_copy_nvidia_does_not_say_vertex(monkeypatch):
    monkeypatch.setenv("PIPELINE_LLM_PROVIDER", "nvidia")
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")
    msg = friendly_pipeline_429_message()
    assert "Vertex" not in msg
    assert "NVIDIA" in msg


def test_429_copy_gemini_does_not_say_vertex(monkeypatch):
    monkeypatch.setenv("PIPELINE_LLM_PROVIDER", "gemini")
    msg = friendly_pipeline_429_message()
    assert "Vertex" not in msg


def test_gemini_side_tools_off_when_nvidia(monkeypatch):
    monkeypatch.setenv("PIPELINE_LLM_PROVIDER", "nvidia")
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")
    monkeypatch.delenv("GEMINI_SIDE_TOOLS", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "AIzaSyfake")
    assert gemini_side_tools_ok() is False


def test_gemini_side_tools_opt_in(monkeypatch):
    monkeypatch.setenv("PIPELINE_LLM_PROVIDER", "nvidia")
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")
    monkeypatch.setenv("GEMINI_SIDE_TOOLS", "1")
    monkeypatch.setenv("GOOGLE_API_KEY", "AIzaSyfake")
    assert gemini_side_tools_ok() is True


def test_explicit_ollama(monkeypatch):
    monkeypatch.setenv("PIPELINE_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:3b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.delenv("GEMINI_SIDE_TOOLS", raising=False)

    assert pipeline_llm_provider() == "ollama"
    assert using_pipeline_litellm() is True
    assert using_pipeline_nvidia() is False
    m = resolve_pipeline_model("gemini-3.6-flash")
    assert "llama3.2:3b" in getattr(m, "model", "")
    assert callable(getattr(m, "generate_content_async", None))
    assert gemini_side_tools_ok() is False


def test_nvidia_attaches_ollama_fallback(monkeypatch):
    monkeypatch.setenv("PIPELINE_LLM_PROVIDER", "nvidia")
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")
    monkeypatch.delenv("PIPELINE_OLLAMA_FALLBACK", raising=False)
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:3b")
    m = resolve_pipeline_model("gemini-3.6-flash")
    assert pipeline_ollama_fallback_enabled() is True
    assert getattr(m, "_ollama_fallback_model", None)
    assert "llama3.2:3b" in m._ollama_fallback_model


def test_nvidia_can_disable_ollama_fallback(monkeypatch):
    monkeypatch.setenv("PIPELINE_LLM_PROVIDER", "nvidia")
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")
    monkeypatch.setenv("PIPELINE_OLLAMA_FALLBACK", "0")
    m = resolve_pipeline_model("gemini-3.6-flash")
    assert pipeline_ollama_fallback_enabled() is False
    assert not getattr(m, "ollama_fallback_model", None)
    assert callable(getattr(m, "generate_content_async", None))
