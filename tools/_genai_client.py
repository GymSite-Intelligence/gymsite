"""
Helper centralizado pra construir clients google-genai cientes de Vertex.

Quando `GOOGLE_GENAI_USE_VERTEXAI=true`:
- Cliente lê GOOGLE_CLOUD_PROJECT/LOCATION + GOOGLE_APPLICATION_CREDENTIALS
  do env e autentica via Service Account (ADC).
- Passar `api_key` faz o google-genai tentar "API Key on Vertex" (modo
  experimental que retorna 401 sem ativação prévia) — então NÃO passa.

Quando `GOOGLE_GENAI_USE_VERTEXAI=false` (ou ausente):
- Cliente usa Gemini Developer API com `api_key`.

Uso:
    from tools._genai_client import build_genai_client, generate_content_resilient
    client = build_genai_client()
    response = generate_content_resilient(client, model="gemini-3.6-flash", contents=...)
"""
from __future__ import annotations

import os
import random
import time
from typing import Any

# Palavras-chave compartilhadas (429 / quota / rate limit).
_RESOURCE_EXHAUSTED_KEYWORDS = (
    "429",
    "resource_exhausted",
    "resourceexhausted",
    "quota",
    "rate limit",
    "too many requests",
)


def is_vertex_mode() -> bool:
    return os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true"


def _sanitize_application_credentials() -> None:
    """Cloud Run usa metadata SA; path local de dev quebra ADC se o arquivo não existe."""
    creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if creds and not os.path.isfile(creds):
        os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)


def build_genai_client():
    """Retorna `genai.Client` apropriado pro modo ativo."""
    from google import genai

    if is_vertex_mode():
        _sanitize_application_credentials()
        return genai.Client()

    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")).strip()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY/GOOGLE_API_KEY não configurada (e VERTEXAI desligado). "
            "Crie em https://aistudio.google.com/apikey (formato AIzaSy...) "
            "ou use GOOGLE_GENAI_USE_VERTEXAI=true + service account JSON."
        )
    if api_key.startswith("AQ."):
        raise RuntimeError(
            "GOOGLE_API_KEY no formato AQ.* (Gemini express) não funciona no pipeline ADK "
            "nem na API generativelanguage.googleapis.com. Use chave AIzaSy... do AI Studio "
            "ou GOOGLE_GENAI_USE_VERTEXAI=true com GOOGLE_APPLICATION_CREDENTIALS."
        )
    return genai.Client(api_key=api_key)


def is_resource_exhausted(exc: BaseException) -> bool:
    """True se o erro indica 429 / RESOURCE_EXHAUSTED (Vertex ou Developer API)."""
    if isinstance(exc, BaseExceptionGroup):
        return any(is_resource_exhausted(sub) for sub in exc.exceptions)
    name = type(exc).__name__.lower()
    if "resourceexhausted" in name:
        return True
    msg = str(exc).lower()
    return any(k in msg for k in _RESOURCE_EXHAUSTED_KEYWORDS)


def _backoff_delay_sec(attempt: int, *, base_delay: float) -> float:
    """Exponential backoff + jitter uniforme [0, 1)."""
    return base_delay * (2**attempt) + random.uniform(0, 1)


def generate_content_resilient(
    client: Any,
    *,
    model: str,
    contents: Any,
    config: Any = None,
    max_retries: int = 3,
    base_delay: float = 4.0,
) -> Any:
    """
    Chama client.models.generate_content com retry em 429 RESOURCE_EXHAUSTED.

    max_retries: tentativas totais (1 = sem retry extra após a primeira falha).
    base_delay: segundos na primeira espera (dobra a cada tentativa + jitter).
    """
    last_exc: BaseException | None = None
    attempts = max(1, int(max_retries))
    for attempt in range(attempts):
        try:
            kwargs: dict[str, Any] = {"model": model, "contents": contents}
            if config is not None:
                kwargs["config"] = config
            return client.models.generate_content(**kwargs)
        except Exception as e:
            last_exc = e
            if not is_resource_exhausted(e) or attempt >= attempts - 1:
                raise
            time.sleep(_backoff_delay_sec(attempt, base_delay=base_delay))
    assert last_exc is not None
    raise last_exc
