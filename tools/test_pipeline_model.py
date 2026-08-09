"""PIPELINE_LLM_PROVIDER resolve — nvidia fora do Vertex billing."""
from __future__ import annotations

import os

from tools.pipeline_model import pipeline_llm_provider, resolve_pipeline_model, using_pipeline_nvidia


def test_explicit_nvidia(monkeypatch):
    monkeypatch.setenv("PIPELINE_LLM_PROVIDER", "nvidia")
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")
    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")
    assert pipeline_llm_provider() == "nvidia"
    assert using_pipeline_nvidia() is True
    from google.adk.models.lite_llm import LiteLlm

    m = resolve_pipeline_model("gemini-2.5-flash")
    assert isinstance(m, LiteLlm)


def test_explicit_vertex(monkeypatch):
    monkeypatch.setenv("PIPELINE_LLM_PROVIDER", "vertex")
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    assert pipeline_llm_provider() == "vertex"
    assert resolve_pipeline_model("gemini-2.5-flash") == "gemini-2.5-flash"


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
