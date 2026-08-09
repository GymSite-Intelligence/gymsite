"""Rota LLM da degustação/consultor — Developer API quando há fallback key.

Pipeline A0–A9 permanece em Vertex (env estrito). Chat do site usa AI Studio
pra não morrer no 403 Lightning dunning do projeto Vertex.
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Iterator

logger = logging.getLogger("gymsite.site_llm_route")

_MSG_DUNNING = (
    "No momento não consigo consultar o modelo de IA (cobrança/projeto Google "
    "temporariamente bloqueado). Tente de novo em alguns minutos — se persistir, "
    "avise o suporte GymSite."
)
_MSG_QUOTA = (
    "A cota do modelo de IA estourou agora. Espere um minuto e tente de novo."
)
_MSG_GENERICO = (
    "Tive um problema ao gerar a resposta agora. Pode reformular a pergunta "
    "ou tentar de novo em instantes?"
)


def is_vertex_dunning(exc: BaseException) -> bool:
    if isinstance(exc, BaseExceptionGroup):
        return any(is_vertex_dunning(sub) for sub in exc.exceptions)
    msg = str(exc).lower()
    return "dunning" in msg or (
        "permission_denied" in msg and "lightning" in msg
    )


def mensagem_falha_turno(exc: BaseException) -> str:
    if is_vertex_dunning(exc):
        return _MSG_DUNNING
    from tools._genai_client import is_resource_exhausted

    if is_resource_exhausted(exc):
        return _MSG_QUOTA
    return _MSG_GENERICO


def _invalidate_gemini_clients(agente_obj) -> None:
    seen: set[int] = set()
    stack = [agente_obj]
    while stack:
        agent = stack.pop()
        aid = id(agent)
        if aid in seen:
            continue
        seen.add(aid)
        model = getattr(agent, "model", None)
        if model is not None and hasattr(model, "__dict__"):
            model.__dict__.pop("api_client", None)
            model.__dict__.pop("_api_backend", None)
            model.__dict__.pop("_live_api_client", None)
            model.__dict__.pop("_base_url_and_api_version", None)
        for sub in getattr(agent, "sub_agents", None) or []:
            stack.append(sub)


def _developer_api_enabled() -> bool:
    flag = (os.getenv("SITE_CHAT_USE_DEVELOPER_API") or "1").strip().lower()
    return flag in ("1", "true", "yes", "on")


def _fallback_api_key() -> str:
    return (
        os.getenv("GYMSITE_GEMINI_FALLBACK_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or ""
    ).strip()


@contextmanager
def site_chat_developer_api(agente_obj) -> Iterator[bool]:
    """Ativa Developer API no processo só durante o turno do chat.

    Retorna True se a rota Developer ficou ativa; False se ficou no env atual.
    Com LiteLlm (ollama|nvidia), não mexe — modelo já não é Gemini nativo.
    """
    from agents_site.model_provider import using_litellm_chat, using_nvidia, using_ollama

    if using_litellm_chat():
        if using_nvidia():
            logger.info("site_chat: rota NVIDIA ativa — skip Developer API")
        elif using_ollama():
            logger.info("site_chat: rota Ollama ativa — skip Developer API")
        yield False
        return

    key = _fallback_api_key()
    if not _developer_api_enabled() or not key:
        yield False
        return

    prev_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI")
    prev_gemini = os.environ.get("GEMINI_API_KEY")
    prev_google = os.environ.get("GOOGLE_API_KEY")
    try:
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "false"
        os.environ["GEMINI_API_KEY"] = key
        os.environ.pop("GOOGLE_API_KEY", None)
        _invalidate_gemini_clients(agente_obj)
        logger.info("site_chat: rota Developer API ativa (fallback key)")
        yield True
    finally:
        if prev_vertex is None:
            os.environ.pop("GOOGLE_GENAI_USE_VERTEXAI", None)
        else:
            os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = prev_vertex
        if prev_gemini is None:
            os.environ.pop("GEMINI_API_KEY", None)
        else:
            os.environ["GEMINI_API_KEY"] = prev_gemini
        if prev_google is None:
            os.environ.pop("GOOGLE_API_KEY", None)
        else:
            os.environ["GOOGLE_API_KEY"] = prev_google
        _invalidate_gemini_clients(agente_obj)
