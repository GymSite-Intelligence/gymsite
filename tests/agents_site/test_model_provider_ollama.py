"""LLM_PROVIDER + Redis override → Gemini / Ollama / NVIDIA."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from agents_site.model_provider import (
    invalidate_llm_provider_cache,
    llm_provider,
    resolve_site_model,
    using_litellm_chat,
    using_nvidia,
    using_ollama,
)


def _clear_provider_env(extra: dict[str, str] | None = None):
    env = {
        "LLM_PROVIDER": "gemini",
        "GYMSITE_SITE_MODEL": "gemini-2.5-flash",
        "SITE_CHAT_ALLOW_OLLAMA": "",
        "NVIDIA_API_KEY": "",
        "NVIDIA_MODEL": "meta/llama-3.1-8b-instruct",
    }
    if extra:
        env.update(extra)
    return patch.dict(os.environ, env, clear=False)


def test_using_ollama_respeita_provider():
    invalidate_llm_provider_cache()
    with _clear_provider_env({"LLM_PROVIDER": "ollama"}), patch(
        "agents_site.model_provider._read_redis_override", return_value=None
    ):
        os.environ.pop("K_SERVICE", None)
        assert using_ollama() is True


def test_using_ollama_ignorado_no_cloud_run():
    invalidate_llm_provider_cache()
    with _clear_provider_env({"LLM_PROVIDER": "ollama", "K_SERVICE": "gymsite-api"}), patch(
        "agents_site.model_provider._read_redis_override", return_value=None
    ):
        assert using_ollama() is False


def test_resolve_gemini_default():
    invalidate_llm_provider_cache()
    with _clear_provider_env({"LLM_PROVIDER": "gemini"}), patch(
        "agents_site.model_provider._read_redis_override", return_value=None
    ):
        os.environ.pop("K_SERVICE", None)
        assert resolve_site_model() == "gemini-2.5-flash"


def test_resolve_ollama_litellm():
    invalidate_llm_provider_cache()
    with _clear_provider_env(
        {
            "LLM_PROVIDER": "ollama",
            "OLLAMA_MODEL": "qwen2.5:7b",
            "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
        }
    ), patch("agents_site.model_provider._read_redis_override", return_value=None):
        os.environ.pop("K_SERVICE", None)
        m = resolve_site_model()
        assert type(m).__name__ == "LiteLlm"
        assert "qwen2.5:7b" in getattr(m, "model", "")


def test_resolve_nvidia_litellm():
    invalidate_llm_provider_cache()
    with _clear_provider_env(
        {
            "LLM_PROVIDER": "nvidia",
            "NVIDIA_API_KEY": "nvapi-test",
            "NVIDIA_MODEL": "meta/llama-3.1-8b-instruct",
        }
    ), patch("agents_site.model_provider._read_redis_override", return_value=None):
        os.environ.pop("K_SERVICE", None)
        assert using_nvidia() is True
        assert using_litellm_chat() is True
        m = resolve_site_model()
        assert type(m).__name__ == "LiteLlm"
        assert "nvidia_nim/" in getattr(m, "model", "")
        assert "llama-3.1-8b-instruct" in getattr(m, "model", "")


def test_redis_override_vence_env():
    invalidate_llm_provider_cache()
    with _clear_provider_env({"LLM_PROVIDER": "ollama"}), patch(
        "agents_site.model_provider._read_redis_override", return_value="nvidia"
    ):
        os.environ.pop("K_SERVICE", None)
        assert llm_provider() == "nvidia"
        assert using_ollama() is False
        assert using_nvidia() is True
