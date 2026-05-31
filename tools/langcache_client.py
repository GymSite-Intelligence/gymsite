# tools/langcache_client.py — Redis LangCache (semantic cache para respostas LLM)
"""
Cache semântico via Redis LangCache — reduz latência e chamadas Gemini repetidas.

Env (server-side):
  LANGCACHE_SERVER_URL   default: https://gcp-us-east4.langcache.redis.io
  LANGCACHE_CACHE_ID     ex: f18755aa86ce413aa7942bdba350e5b9
  LANGCACHE_API_KEY      prefixo lc1_ (ou REDIS_GENERATE_KEY legado)
  LANGCACHE_EMBEDDING_MODEL  informativo — definido no cache Redis Cloud
  LANGCACHE_SIMILARITY_THRESHOLD  default 0.85
  LANGCACHE_ENABLED      default true quando credenciais presentes
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Iterator, Optional

logger = logging.getLogger("gymsite.langcache")

_DEFAULT_SERVER = "https://gcp-us-east4.langcache.redis.io"
_DEFAULT_THRESHOLD = 0.85


def _truthy(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def get_langcache_api_key() -> str:
    return (
        os.getenv("LANGCACHE_API_KEY")
        or os.getenv("REDIS_GENERATE_KEY")
        or ""
    ).strip()


def is_langcache_configured() -> bool:
    if not _truthy("LANGCACHE_ENABLED", default=True):
        return False
    return bool(get_langcache_api_key() and os.getenv("LANGCACHE_CACHE_ID", "").strip())


def get_similarity_threshold() -> float:
    try:
        return float(os.getenv("LANGCACHE_SIMILARITY_THRESHOLD", _DEFAULT_THRESHOLD))
    except ValueError:
        return _DEFAULT_THRESHOLD


@contextmanager
def langcache_session() -> Iterator[Any]:
    from langcache import LangCache

    with LangCache(
        server_url=os.getenv("LANGCACHE_SERVER_URL", _DEFAULT_SERVER).strip(),
        cache_id=os.getenv("LANGCACHE_CACHE_ID", "").strip(),
        api_key=get_langcache_api_key(),
    ) as client:
        yield client


def langcache_search(
    prompt: str,
    *,
    attributes: Optional[dict[str, str]] = None,
    similarity_threshold: Optional[float] = None,
) -> Optional[str]:
    """Busca semântica. Retorna response se hit, senão None."""
    if not is_langcache_configured():
        return None
    text = (prompt or "").strip()
    if not text:
        return None
    threshold = (
        similarity_threshold
        if similarity_threshold is not None
        else get_similarity_threshold()
    )
    try:
        with langcache_session() as lc:
            search_kwargs: dict[str, Any] = {
                "prompt": text[:1024],
                "similarity_threshold": threshold,
            }
            if attributes:
                search_kwargs["attributes"] = attributes
            result = lc.search(**search_kwargs)
            entries = getattr(result, "data", None) or []
            if not entries:
                return None
            best = entries[0]
            response = getattr(best, "response", None)
            if response and str(response).strip():
                logger.debug(
                    "LangCache hit similarity=%.3f prompt=%.80s",
                    getattr(best, "similarity", 0),
                    text,
                )
                return str(response)
    except Exception as e:
        logger.warning("LangCache search failed: %s", e)
    return None


def langcache_set(
    prompt: str,
    response: str,
    *,
    attributes: Optional[dict[str, str]] = None,
    ttl_millis: Optional[int] = None,
) -> bool:
    """Grava par prompt/response no cache semântico."""
    if not is_langcache_configured():
        return False
    p = (prompt or "").strip()
    r = (response or "").strip()
    if not p or not r:
        return False
    try:
        kwargs: dict[str, Any] = {
            "prompt": p[:1024],
            "response": r,
        }
        if attributes:
            kwargs["attributes"] = attributes
        if ttl_millis is not None:
            kwargs["ttl_millis"] = ttl_millis
        with langcache_session() as lc:
            lc.set(**kwargs)
        return True
    except Exception as e:
        logger.warning("LangCache set failed: %s", e)
        return False
