"""Resolve modelo dos agentes do site (Gemini / Ollama / NVIDIA NIM).

Env (defaults — secrets só aqui / Secret Manager):
  LLM_PROVIDER=nvidia|ollama|local|gemini   (default gemini)
  OLLAMA_MODEL=qwen2.5:7b
  OLLAMA_BASE_URL=http://127.0.0.1:11434
  NVIDIA_API_KEY=…
  NVIDIA_MODEL=nvidia/nemotron-3-nano-30b-a3b
  GYMSITE_SITE_MODEL=gemini-3.6-flash

Override runtime (admin): Redis key `gymsite:llm_provider` — sem secrets.
Cloud Run ignora ollama (K_SERVICE) a menos que SITE_CHAT_ALLOW_OLLAMA=1.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Literal

from tools.pipeline_model import DEFAULT_NVIDIA_MODEL

logger = logging.getLogger("gymsite.site_model")

REDIS_PROVIDER_KEY = "gymsite:llm_provider"
VALID_PROVIDERS = frozenset({"nvidia", "ollama", "local", "gemini"})
ProviderName = Literal["nvidia", "ollama", "local", "gemini"]

_CACHE_TTL_S = 2.0
_cache_at: float = 0.0
_cache_val: str | None = None


def invalidate_llm_provider_cache() -> None:
    global _cache_at, _cache_val
    _cache_at = 0.0
    _cache_val = None


def _read_redis_override() -> str | None:
    """Best-effort sync read; Redis down → None (fallback .env)."""
    global _cache_at, _cache_val
    now = time.monotonic()
    if now - _cache_at < _CACHE_TTL_S:
        return _cache_val
    val: str | None = None
    try:
        from tools.redis_client import get_redis_sync

        raw = get_redis_sync().get(REDIS_PROVIDER_KEY)
        if isinstance(raw, str):
            cand = raw.strip().lower()
            if cand in VALID_PROVIDERS:
                val = cand
    except Exception as exc:  # noqa: BLE001
        logger.debug("llm_provider redis override miss: %s", exc)
    _cache_at = now
    _cache_val = val
    return val


def llm_provider_env() -> str:
    return (os.getenv("LLM_PROVIDER") or "gemini").strip().lower()


def llm_provider() -> str:
    ov = _read_redis_override()
    if ov:
        return ov
    return llm_provider_env()


def llm_provider_source() -> Literal["redis", "env"]:
    return "redis" if _read_redis_override() else "env"


def using_ollama() -> bool:
    p = llm_provider()
    if p not in ("ollama", "local"):
        return False
    if os.getenv("K_SERVICE") and (os.getenv("SITE_CHAT_ALLOW_OLLAMA") or "").strip() != "1":
        return False
    return True


def using_nvidia() -> bool:
    return llm_provider() == "nvidia"


def using_litellm_chat() -> bool:
    """Ollama ou NVIDIA — LiteLlm; skip rota Developer API Gemini."""
    return using_ollama() or using_nvidia()


def _display_model_for(provider: str) -> str:
    if provider in ("ollama", "local"):
        return (os.getenv("OLLAMA_MODEL") or "qwen2.5:7b").strip()
    if provider == "nvidia":
        return (os.getenv("NVIDIA_MODEL") or DEFAULT_NVIDIA_MODEL).strip()
    return (os.getenv("GYMSITE_SITE_MODEL") or "gemini-3.6-flash").strip()


def llm_config_snapshot() -> dict[str, Any]:
    """Status admin (sem secrets)."""
    effective = llm_provider()
    override = _read_redis_override()
    return {
        "provider": effective,
        "provider_env": llm_provider_env(),
        "provider_override": override,
        "source": llm_provider_source(),
        "model": _display_model_for(effective),
        "options": ["nvidia", "ollama"],
        "nvidia_key_configured": bool((os.getenv("NVIDIA_API_KEY") or "").strip()),
        "cloud_run": bool(os.getenv("K_SERVICE")),
        "ollama_allowed_on_cloud": (os.getenv("SITE_CHAT_ALLOW_OLLAMA") or "").strip() == "1",
    }


def resolve_site_model() -> Any:
    """String Gemini (ADK nativo) ou LiteLlm(ollama|nvidia_nim/…)."""
    if using_ollama():
        from google.adk.models.lite_llm import LiteLlm

        base = (os.getenv("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/")
        model_name = (os.getenv("OLLAMA_MODEL") or "qwen2.5:7b").strip()
        os.environ.setdefault("OLLAMA_API_BASE", base)
        litellm_id = model_name if model_name.startswith("ollama/") else f"ollama/{model_name}"
        logger.info("site_chat model=Ollama %s @ %s", litellm_id, base)
        return LiteLlm(model=litellm_id, api_base=base)

    if using_nvidia():
        from google.adk.models.lite_llm import LiteLlm

        api_key = (os.getenv("NVIDIA_API_KEY") or "").strip()
        if not api_key:
            logger.error("LLM_PROVIDER=nvidia sem NVIDIA_API_KEY — chat vai falhar")
        model_name = (os.getenv("NVIDIA_MODEL") or DEFAULT_NVIDIA_MODEL).strip()
        # LiteLLM aceita NVIDIA_NIM_API_KEY; espelha a key do projeto.
        if api_key:
            os.environ.setdefault("NVIDIA_NIM_API_KEY", api_key)
        litellm_id = (
            model_name
            if model_name.startswith("nvidia_nim/")
            else f"nvidia_nim/{model_name}"
        )
        logger.info("site_chat model=NVIDIA %s", litellm_id)
        return LiteLlm(model=litellm_id, api_key=api_key or None)

    return (os.getenv("GYMSITE_SITE_MODEL") or "gemini-3.6-flash").strip()
