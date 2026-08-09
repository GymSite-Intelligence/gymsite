"""Factory canônica de LlmAgent (CONSTITUTION C5.2/C5.4/C7.2).

Todo agente LLM nasce conforme: ACL (retry no modelo p/ 429/503/500 — retenta a
CHAMADA, não a pipeline) + telemetria de tokens — aplicados na CONSTRUÇÃO, não
dependendo do attach central. Assim agentes fora do Runner (A7 importado como
função, A8 via a8_runner, root_agent) também ficam instrumentados.

Idempotente com gymsite_intelligence.agent._attach_telemetry: os callbacks
deduplicam por identidade (chain só encadeia callbacks distintos) e o wrap de
retry só roda quando `model` ainda é string.

Uso (substitui `Agent(...)` direto):
    from tools.agent_factory import build_llm_agent
    meu_agente = build_llm_agent(name="X", model="gemini-2.5-flash", instruction=...)
"""
from __future__ import annotations

from typing import Any


def _retry_options():
    """HttpRetryOptions p/ o modelo (mesma config do _attach_telemetry). None se ADK ausente."""
    try:
        from google.genai import types

        return types.HttpRetryOptions(
            attempts=4, initial_delay=2.0, max_delay=60.0, exp_base=2.0,
            http_status_codes=[429, 503, 500],
        )
    except Exception:
        return None


def _wrap_model_com_retry(kwargs: dict[str, Any]) -> None:
    """model string → Gemini(retry_options) (ACL C5.4). Best-effort; mantém string se falhar."""
    model = kwargs.get("model")
    if not (isinstance(model, str) and model.strip()):
        return
    try:
        from google.adk.models.google_llm import Gemini

        ro = _retry_options()
        if ro is not None:
            kwargs["model"] = Gemini(model=model, retry_options=ro)
    except Exception:
        pass  # ADK indisponível neste contexto — segue com a string


def _injetar_telemetria(kwargs: dict[str, Any]) -> None:
    """after_model_callback de tokens (C7.2). Encadeia se o agente já trouxe o seu —
    conserta o furo do _attach_telemetry (que PULAVA quem já tinha callback, ex: A9)."""
    try:
        from tools.token_telemetry import after_model_callback as _telemetry
    except Exception:
        return
    existing = kwargs.get("after_model_callback")
    if existing is None or existing is _telemetry:
        kwargs["after_model_callback"] = _telemetry
        return

    def _chained(*a, **k):
        existing(*a, **k)
        _telemetry(*a, **k)

    kwargs["after_model_callback"] = _chained


def _strip_gemini_only_config(kwargs: dict[str, Any]) -> None:
    """thinking_config / extras Gemini quebram LiteLlm(NVIDIA) — remove no path nvidia."""
    from tools.pipeline_model import using_pipeline_nvidia

    if not using_pipeline_nvidia():
        return
    kwargs.pop("generate_content_config", None)


def build_llm_agent(**kwargs: Any):
    """Constrói um google.adk.agents.Agent com ACL (retry) + telemetria já aplicados."""
    from google.adk.agents import Agent

    from tools.pipeline_model import resolve_pipeline_model

    model = kwargs.get("model")
    if isinstance(model, str) and model.strip():
        kwargs["model"] = resolve_pipeline_model(model)
    _strip_gemini_only_config(kwargs)
    _wrap_model_com_retry(kwargs)
    _injetar_telemetria(kwargs)
    return Agent(**kwargs)
