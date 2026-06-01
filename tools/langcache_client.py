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

Atributos (opcional no Redis Cloud LangCache console):
  prompt_hash (string), agent (string) — se não configurados, SET/SEARCH
  fazem fallback sem attributes (ver _attributes_not_configured).
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Iterator, Optional

logger = logging.getLogger("gymsite.langcache")

_DEFAULT_SERVER = "https://gcp-us-east4.langcache.redis.io"
_DEFAULT_THRESHOLD = 0.85
_DEFAULT_TTL_MS = int(os.getenv("LANGCACHE_DEFAULT_TTL_MS", str(7 * 24 * 60 * 60 * 1000)))  # 7 dias


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


def _attributes_not_configured(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "no attributes are configured" in msg


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
    """Busca semântica com métricas de hit/miss."""
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
    attr_attempts: list[Optional[dict[str, str]]] = [attributes] if attributes else [None]
    if attributes:
        attr_attempts.append(None)

    last_error: Optional[Exception] = None
    for attrs in attr_attempts:
        try:
            with langcache_session() as lc:
                search_kwargs: dict[str, Any] = {
                    "prompt": text[:1024],
                    "similarity_threshold": threshold,
                }
                if attrs:
                    search_kwargs["attributes"] = attrs
                result = lc.search(**search_kwargs)
                entries = getattr(result, "data", None) or []
                if not entries:
                    logger.debug(
                        "LangCache MISS | threshold=%.2f | prompt=%.80s",
                        threshold,
                        text,
                        extra={"langcache": True, "cache_hit": False},
                    )
                    return None
                best = entries[0]
                response = getattr(best, "response", None)
                similarity = getattr(best, "similarity", 0)
                if response and str(response).strip():
                    logger.info(
                        "LangCache HIT | similarity=%.3f | threshold=%.2f | prompt=%.80s",
                        similarity,
                        threshold,
                        text,
                        extra={"langcache": True, "cache_hit": True, "similarity": similarity},
                    )
                    return str(response)
                logger.debug(
                    "LangCache HIT but empty response | similarity=%.3f",
                    similarity,
                    extra={"langcache": True, "cache_hit": False},
                )
                return None
        except Exception as e:
            last_error = e
            if attrs and _attributes_not_configured(e):
                logger.warning(
                    "LangCache attributes não configurados no cache — search sem attributes",
                    extra={"langcache": True},
                )
                continue
            logger.warning(
                "LangCache search failed: %s",
                e,
                exc_info=True,
                extra={"langcache": True},
            )
            return None

    if last_error:
        logger.warning(
            "LangCache search failed após retries: %s",
            last_error,
            exc_info=True,
            extra={"langcache": True},
        )
    return None


def langcache_set(
    prompt: str,
    response: str,
    *,
    attributes: Optional[dict[str, str]] = None,
    ttl_millis: Optional[int] = None,
) -> bool:
    """Grava par prompt/response no cache semântico com TTL."""
    if not is_langcache_configured():
        return False
    p = (prompt or "").strip()
    r = (response or "").strip()
    if not p or not r:
        return False

    # Usa TTL default se não especificado
    if ttl_millis is None:
        ttl_millis = _DEFAULT_TTL_MS

    attr_attempts: list[Optional[dict[str, str]]] = [attributes] if attributes else [None]
    if attributes:
        attr_attempts.append(None)

    last_error: Optional[Exception] = None
    for attrs in attr_attempts:
        try:
            kwargs: dict[str, Any] = {
                "prompt": p[:1024],
                "response": r,
                "ttl_millis": ttl_millis,
            }
            if attrs:
                kwargs["attributes"] = attrs
            with langcache_session() as lc:
                lc.set(**kwargs)
            logger.debug(
                "LangCache SET OK | ttl=%dms | attrs=%s | prompt=%.80s",
                ttl_millis,
                bool(attrs),
                p,
                extra={"langcache": True},
            )
            return True
        except Exception as e:
            last_error = e
            if attrs and _attributes_not_configured(e):
                logger.warning(
                    "LangCache attributes não configurados no cache — set sem attributes",
                    extra={"langcache": True},
                )
                continue
            logger.warning(
                "LangCache set failed: %s",
                e,
                exc_info=True,
                extra={"langcache": True},
            )
            return False

    if last_error:
        logger.warning(
            "LangCache set failed após retries: %s",
            last_error,
            exc_info=True,
            extra={"langcache": True},
        )
    return False
