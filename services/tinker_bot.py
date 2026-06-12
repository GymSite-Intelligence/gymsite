"""Tinker Bot Service — wrapper de inference via Tinker SamplingClient
com fallback para Gemini quando o Tinker não está disponível (ex: 402 billing).

Documentação: https://tinker-docs.thinkingmachines.ai/tinker/quickstart/
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy-init cached clients
_service_client = None
_sampling_client = None
_tokenizer = None


def _get_service_client():
    global _service_client
    if _service_client is None:
        import tinker
        _service_client = tinker.ServiceClient()
    return _service_client


def _get_sampling_client():
    global _sampling_client, _tokenizer
    if _sampling_client is None:
        import tinker
        base_model = os.getenv("TINKER_BASE_MODEL", "Qwen/Qwen3-8B")
        _sampling_client = _get_service_client().create_sampling_client(base_model=base_model)
        _tokenizer = _sampling_client.get_tokenizer()
    return _sampling_client


def _get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        _get_sampling_client()
    return _tokenizer


def _gemini_chat(prompt_text: str, max_tokens: int = 1024, temperature: float = 0.7) -> str:
    """Fallback — usa Gemini (google-genai) quando o Tinker falha.

    thinking_budget limitado + piso de 2048 tokens: no Gemini 2.5 os thought
    tokens CONSOMEM max_output_tokens (BUG-009) — sem teto, respostas do chat
    saíam truncadas no meio da frase ("...ex: Smart Fit," e cortava)."""
    from tools._genai_client import build_genai_client, generate_content_resilient
    from google.genai import types as genai_types

    client = build_genai_client()
    model = os.getenv("TINKER_FALLBACK_MODEL", "gemini-2.5-flash")

    response = generate_content_resilient(
        client,
        model=model,
        contents=prompt_text,
        config=genai_types.GenerateContentConfig(
            max_output_tokens=max(max_tokens, 2048),
            temperature=temperature,
            thinking_config=genai_types.ThinkingConfig(thinking_budget=256),  # pyright: ignore[reportCallIssue]
        ),
    )
    return response.text or ""


async def chat_async(
    prompt_text: str,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    top_p: float = 0.9,
    stop_sequences: Optional[list[str]] = None,
) -> str:
    """Envia um prompt texto para o Tinker SamplingClient e retorna a resposta decodificada.

    Se o Tinker falhar (ex: 402 billing, auth error, timeout), faz fallback
    automático para Gemini (google-genai) que já está configurado no projeto.
    """
    # Tentativa 1 — Tinker (prioridade quando disponível)
    try:
        sampling_client = _get_sampling_client()
        tokenizer = _get_tokenizer()

        import tinker
        prompt = tinker.types.ModelInput.from_ints(tokenizer.encode(prompt_text))
        params = tinker.types.SamplingParams(
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=stop_sequences or [],
        )
        result = await sampling_client.sample_async(
            prompt=prompt,
            num_samples=1,
            sampling_params=params,
        )
        if result.sequences:
            return tokenizer.decode(result.sequences[0].tokens)
        return ""
    except Exception as e:
        error_msg = str(e).lower()
        if "402" in error_msg or "billing" in error_msg or "payment" in error_msg:
            logger.warning("Tinker indisponível (402 billing). Fallback para Gemini.")
        else:
            logger.warning("Tinker falhou (%s). Fallback para Gemini.", e)

    # Tentativa 2 — Gemini fallback
    try:
        return _gemini_chat(prompt_text, max_tokens=max_tokens, temperature=temperature)
    except Exception as e:
        logger.exception("Gemini fallback também falhou: %s", e)
        raise RuntimeError(f"Assistente indisponível. Tinker: billing bloqueado. Gemini: {e}")


def reset_client() -> None:
    """Reseta os clients cached (útil para testes ou troca de modelo)."""
    global _service_client, _sampling_client, _tokenizer
    _service_client = None
    _sampling_client = None
    _tokenizer = None
