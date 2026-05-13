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
    from tools._genai_client import build_genai_client
    client = build_genai_client()  # lança RuntimeError se config inválida
"""
from __future__ import annotations

import os


def is_vertex_mode() -> bool:
    return os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true"


def build_genai_client():
    """Retorna `genai.Client` apropriado pro modo ativo."""
    from google import genai

    if is_vertex_mode():
        # Vertex: project + location + ADC vêm do env.
        return genai.Client()

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY/GOOGLE_API_KEY não configurada (e VERTEXAI desligado)"
        )
    return genai.Client(api_key=api_key)
