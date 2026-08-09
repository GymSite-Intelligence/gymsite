"""Admin — provedor LLM do chat (consultor / site).

Override em Redis (`gymsite:llm_provider`); secrets ficam no .env.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from agents_site.model_provider import (
    REDIS_PROVIDER_KEY,
    VALID_PROVIDERS,
    invalidate_llm_provider_cache,
    llm_config_snapshot,
)
from backend.routers.parceiros_admin import require_admin
from tools.redis_client import get_redis

router = APIRouter(prefix="/api/admin/llm-config", tags=["Admin — LLM"])

ProviderChoice = Literal["nvidia", "ollama", "env"]


class LlmConfigPatch(BaseModel):
    """`env` limpa o override e volta ao LLM_PROVIDER do .env.

    Gemini não entra no PATCH — descontinuado no chat (só via .env legado).
    """

    provider: ProviderChoice = Field(
        ...,
        description="nvidia|ollama|env",
    )


@router.get("")
async def get_llm_config(_admin: dict = Depends(require_admin)):
    return llm_config_snapshot()


@router.patch("")
async def patch_llm_config(body: LlmConfigPatch, _admin: dict = Depends(require_admin)):
    try:
        r = await get_redis()
        if body.provider == "env":
            await r.delete(REDIS_PROVIDER_KEY)
        else:
            if body.provider not in VALID_PROVIDERS:
                raise HTTPException(status_code=400, detail="Provedor inválido")
            await r.set(REDIS_PROVIDER_KEY, body.provider)
        invalidate_llm_provider_cache()
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail=f"Redis indisponível — não deu pra gravar o provedor ({type(exc).__name__})",
        ) from exc
    return llm_config_snapshot()
