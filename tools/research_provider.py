"""
Provedor de pesquisa A0 — Gemini (Deep Research) vs Kimi (OpenClaw).

Definido por:
  1. contextvar `a0_research_provider_ctx` (setado pela API por relatório)
  2. env A0_RESEARCH_PROVIDER (default gemini)
"""
from __future__ import annotations

import contextvars
import os

a0_research_provider_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "a0_research_provider",
    default=None,
)


def set_a0_research_provider(provider: str | None) -> None:
    """Chamado no início do pipeline (API/CLI)."""
    a0_research_provider_ctx.set((provider or "").strip().lower() or None)


def get_a0_research_provider() -> str:
    """
    Retorna 'kimi' ou 'gemini'.
    Valores aceitos no form/env: kimi, openclaw, gemini, auto.
    """
    explicit = a0_research_provider_ctx.get()
    if explicit in ("kimi", "openclaw"):
        return "kimi"
    if explicit == "gemini":
        return "gemini"
    if explicit == "auto":
        env = (os.getenv("A0_RESEARCH_PROVIDER") or "gemini").strip().lower()
        return "kimi" if env in ("kimi", "openclaw") else "gemini"

    env = (os.getenv("A0_RESEARCH_PROVIDER") or "gemini").strip().lower()
    return "kimi" if env in ("kimi", "openclaw") else "gemini"
