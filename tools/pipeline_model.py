"""Backend LLM do pipeline A0–A9 (separado do chat `LLM_PROVIDER`).

Hot-path relatório NÃO depende de Vertex billing.
  PIPELINE_LLM_PROVIDER=nvidia|gemini|vertex|ollama
  PIPELINE_OLLAMA_FALLBACK=1  (default: NVIDIA 429/410 → Ollama na VPS)
  (vazio = auto: vertex se GOOGLE_GENAI_USE_VERTEXAI=true; senão nvidia se
   LLM_PROVIDER=nvidia + key; senão gemini Developer API)

Chat degustação continua em agents_site/model_provider.py.

Modelo Gemini canônico do pipeline: ``gemini-3.6-flash`` (2.5 deprecado).
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("gymsite.pipeline_model")

# Canônico — NÃO usar gemini-2.5-* (deprecado; free-tier 429 / docs desatualizados).
DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"
# Hosted NIM: meta/llama-3.1-8b-instruct EOL 2026-08-26 (HTTP 410 Gone).
DEFAULT_NVIDIA_MODEL = "nvidia/nemotron-3-nano-30b-a3b"
DEFAULT_OLLAMA_MODEL = "llama3.2:3b"

_FAILOVER_HINTS = (
    "429",
    "410",
    "resource_exhausted",
    "too many requests",
    "timeout",
    "timed out",
    "connection",
    "unavailable",
    "503",
    "502",
    "end of life",
    "has reached its end of life",
)


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
    if explicit in ("nvidia", "gemini", "vertex", "ollama"):
        return explicit
    if is_vertex_env():
        return "vertex"
    chat = (os.getenv("LLM_PROVIDER") or "").strip().lower()
    if chat == "nvidia" and (os.getenv("NVIDIA_API_KEY") or "").strip():
        return "nvidia"
    return "gemini"


def using_pipeline_nvidia() -> bool:
    return pipeline_llm_provider() == "nvidia"


def using_pipeline_litellm() -> bool:
    return pipeline_llm_provider() in ("nvidia", "ollama")


def ollama_base_url() -> str:
    return (os.getenv("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/")


def ollama_litellm_model_id() -> str:
    name = (os.getenv("OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL).strip()
    return name if name.startswith("ollama/") else f"ollama/{name}"


def pipeline_ollama_fallback_enabled() -> bool:
    """NVIDIA primário → Ollama na VPS se NIM 429/410/rede. Off: PIPELINE_OLLAMA_FALLBACK=0."""
    if pipeline_llm_provider() != "nvidia":
        return False
    flag = (os.getenv("PIPELINE_OLLAMA_FALLBACK") or "").strip().lower()
    if flag in ("0", "false", "off", "no"):
        return False
    return True


def _should_failover_to_ollama(exc: BaseException) -> bool:
    msg = f"{type(exc).__name__} {exc}".lower()
    return any(h in msg for h in _FAILOVER_HINTS)


def gemini_side_tools_ok() -> bool:
    """Gemini Developer / Vertex Search Grounding — off no hot-path NVIDIA.

    AQ.* = Gemini Express — não autentica generativelanguage.googleapis.com.
    Opt-in: GEMINI_SIDE_TOOLS=1 + chave AIzaSy…
    """
    flag = (os.getenv("GEMINI_SIDE_TOOLS") or "").strip().lower()
    if flag in ("0", "false", "off", "no"):
        return False
    if flag in ("1", "true", "on", "yes"):
        return True
    if using_pipeline_litellm():
        return False
    key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    if not key or key.startswith("AQ."):
        return False
    return True


def friendly_pipeline_429_message() -> str:
    """Texto ao usuário. 429 NVIDIA/LiteLLM NÃO é Vertex (copy legado mentia)."""
    provider = pipeline_llm_provider()
    if provider == "nvidia":
        if pipeline_ollama_fallback_enabled():
            return (
                "Pico de uso do modelo NVIDIA — fallback Ollama na VPS; "
                "tente de novo se persistir"
            )
        return "Pico de uso do modelo NVIDIA — tente de novo em alguns minutos"
    if provider == "ollama":
        return "Ollama na VPS não respondeu — confira se o serviço está no ar"
    if provider == "gemini":
        return "Pico de uso do Gemini — tente de novo em alguns minutos"
    if provider == "vertex":
        return "Pico de uso da Vertex AI — tente de novo em alguns minutos"
    return "Pico de uso do modelo de IA — tente de novo em alguns minutos"


def resolve_pipeline_model(requested: str) -> Any:
    """String Gemini (ADK nativo) ou LiteLlm(nvidia_nim/… | ollama/…)."""
    provider = pipeline_llm_provider()
    name = (requested or DEFAULT_GEMINI_MODEL).strip()
    if name.startswith("gemini-2.5-") or name in (
        "gemini-flash-3.6",
        "gemini-3-flash-preview",
    ):
        logger.info("pipeline model alias %s → %s", name, DEFAULT_GEMINI_MODEL)
        name = DEFAULT_GEMINI_MODEL

    if provider == "ollama":
        return _build_ollama_litellm()

    if provider != "nvidia":
        if provider == "vertex":
            logger.debug("pipeline model=Vertex %s", name)
        else:
            logger.debug("pipeline model=Gemini Developer %s", name)
        return name

    from google.adk.models.lite_llm import LiteLlm

    api_key = (os.getenv("NVIDIA_API_KEY") or "").strip()
    if not api_key:
        logger.error("PIPELINE_LLM_PROVIDER=nvidia sem NVIDIA_API_KEY — Ollama")
        return _build_ollama_litellm()
    os.environ.setdefault("NVIDIA_NIM_API_KEY", api_key)
    model_name = (os.getenv("NVIDIA_MODEL") or DEFAULT_NVIDIA_MODEL).strip()
    litellm_id = (
        model_name
        if model_name.startswith("nvidia_nim/")
        else f"nvidia_nim/{model_name}"
    )
    logger.info("pipeline model=NVIDIA %s (pedido era %s)", litellm_id, name)
    if pipeline_ollama_fallback_enabled():
        fb = ollama_litellm_model_id()
        os.environ.setdefault("OLLAMA_API_BASE", ollama_base_url())
        logger.info("pipeline NVIDIA fallback Ollama %s @ %s", fb, ollama_base_url())
        return NvidiaOllamaFallbackLlm(
            model=litellm_id,
            api_key=api_key,
            ollama_fallback_model=fb,
            ollama_api_base=ollama_base_url(),
        )
    return LiteLlm(model=litellm_id, api_key=api_key)


def _build_ollama_litellm() -> Any:
    from google.adk.models.lite_llm import LiteLlm

    base = ollama_base_url()
    os.environ.setdefault("OLLAMA_API_BASE", base)
    mid = ollama_litellm_model_id()
    logger.info("pipeline model=Ollama %s @ %s", mid, base)
    return LiteLlm(model=mid, api_base=base)


def _define_nvidia_ollama_fallback_llm() -> type:
    from google.adk.models.lite_llm import LiteLlm

    class _NvidiaOllamaFallbackLlm(LiteLlm):
        """LiteLlm NVIDIA; 429/410/rede → uma tentativa Ollama (mesmo worker)."""

        ollama_fallback_model: str = ""
        ollama_api_base: str = ""

        def __init__(
            self,
            model: str,
            *,
            api_key: str,
            ollama_fallback_model: str,
            ollama_api_base: str,
        ) -> None:
            super().__init__(
                model=model,
                api_key=api_key,
                ollama_fallback_model=ollama_fallback_model,
                ollama_api_base=ollama_api_base,
            )
            self._additional_args.pop("ollama_fallback_model", None)
            self._additional_args.pop("ollama_api_base", None)

        @property
        def _ollama_fallback_model(self) -> str:
            return self.ollama_fallback_model

        @property
        def _ollama_api_base(self) -> str:
            return self.ollama_api_base

        async def generate_content_async(self, llm_request: Any, stream: bool = False) -> Any:
            yielded = False
            try:
                async for chunk in super().generate_content_async(llm_request, stream=stream):
                    yielded = True
                    yield chunk
                return
            except Exception as e:
                if yielded or not _should_failover_to_ollama(e):
                    raise
                logger.warning(
                    "pipeline NVIDIA falhou (%s) — tentando Ollama %s",
                    e,
                    self.ollama_fallback_model,
                )

            saved_model = getattr(llm_request, "model", None)
            try:
                if hasattr(llm_request, "model"):
                    llm_request.model = self.ollama_fallback_model
                ollama = LiteLlm(
                    model=self.ollama_fallback_model,
                    api_base=self.ollama_api_base,
                )
                async for chunk in ollama.generate_content_async(llm_request, stream=stream):
                    yield chunk
            finally:
                if hasattr(llm_request, "model"):
                    llm_request.model = saved_model

    return _NvidiaOllamaFallbackLlm


NvidiaOllamaFallbackLlm = _define_nvidia_ollama_fallback_llm()
