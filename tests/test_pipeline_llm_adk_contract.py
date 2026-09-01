"""Contrato ADK: model NVIDIA+Ollama tem que ser BaseLlm (não Vertex/Cloud Run).

Google ADK = orquestrador A0–A9 (ainda vivo).
Vertex billing / Discovery / Cloud Run = deprecados. Este teste só trava o
pydantic do LlmAgent — o bug cc14ef8f.
"""
from __future__ import annotations

from google.adk.agents import Agent
from google.adk.models.base_llm import BaseLlm

from tools.pipeline_model import resolve_pipeline_model


def test_nvidia_fallback_accepted_by_adk_agent(monkeypatch):
    monkeypatch.setenv("PIPELINE_LLM_PROVIDER", "nvidia")
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")
    monkeypatch.delenv("PIPELINE_OLLAMA_FALLBACK", raising=False)
    m = resolve_pipeline_model("gemini-3.6-flash")
    assert isinstance(m, BaseLlm)
    Agent(name="t", model=m, instruction="ok")
