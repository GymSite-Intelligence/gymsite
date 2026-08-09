"""Backend LLM do pipeline A0–A9 (separado do chat `LLM_PROVIDER`).

Hot-path relatório NÃO depende de Vertex billing.
  PIPELINE_LLM_PROVIDER=nvidia|gemini|vertex
  (vazio = auto: vertex se GOOGLE_GENAI_USE_VERTEXAI=true; senão nvidia se
   LLM_PROVIDER=nvidia + key; senão gemini Developer API)

Chat degustação continua em agents_site/model_provider.py.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("gymsite.pipeline_model")


def is_vertex_env() -> bool:
    return (os.getenv("GOOGLE_GENAI_USE_VERTEXAI") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def pipeline_llm_provider() -> str:
    """nvidia | gemini | vertex — resolução efetiva."""
    explicit = (os.getenv("PIPELINE_LLM_PROVIDER") or "").strip().lower()
    if explicit in ("nvidia", "gemini", "vertex"):
        return explicit
    if is_vertex_env():
        return "vertex"
    chat = (os.getenv("LLM_PROVIDER") or "").strip().lower()
    if chat == "nvidia" and (os.getenv("NVIDIA_API_KEY") or "").strip():
        return "nvidia"
    return "gemini"


def using_pipeline_nvidia() -> bool:
    return pipeline_llm_provider() == "nvidia"


def resolve_pipeline_model(requested: str) -> Any:
    """String Gemini (ADK nativo) ou LiteLlm(nvidia_nim/…)."""
    provider = pipeline_llm_provider()
    name = (requested or "gemini-2.5-flash").strip()

    if provider != "nvidia":
        if provider == "vertex":
            logger.debug("pipeline model=Vertex %s", name)
        else:
            logger.debug("pipeline model=Gemini Developer %s", name)
        return name

    from google.adk.models.lite_llm import LiteLlm

    api_key = (os.getenv("NVIDIA_API_KEY") or "").strip()
    if not api_key:
        logger.error(
            "PIPELINE_LLM_PROVIDER=nvidia sem NVIDIA_API_KEY — fallback string Gemini"
        )
        return name
    os.environ.setdefault("NVIDIA_NIM_API_KEY", api_key)
    model_name = (os.getenv("NVIDIA_MODEL") or "meta/llama-3.1-8b-instruct").strip()
    litellm_id = (
        model_name
        if model_name.startswith("nvidia_nim/")
        else f"nvidia_nim/{model_name}"
    )
    logger.info(
        "pipeline model=NVIDIA %s (pedido era %s)",
        litellm_id,
        name,
    )
    return LiteLlm(model=litellm_id, api_key=api_key)
