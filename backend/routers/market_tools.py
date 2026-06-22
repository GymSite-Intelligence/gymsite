"""
Router /api/tools — funções de mercado AO VIVO expostas como OpenAPI/Function p/ o
Agent Builder (Vertex AI). Arquitetura híbrida: o agente do Builder orquestra (Gemini
+ Data Store/RAG), e quando precisa de DADO VIVO que o RAG não tem (concorrentes via
Google Maps, demografia via IBGE/BQ), chama estes endpoints.

LEVE por design: contagem + nomes + saturação por RAIO (sem enrichment de reviews/dores)
→ rápido (~10-20s), cabe no timeout da tool do Builder. O raio (sem filtro de bairro)
conta a competição real do entorno (≈ metodologia do mercado, não subconta o bairro).

Auth: header X-API-Key == env MARKET_TOOLS_API_KEY (a key que você cola na tool do Builder).
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("gymsite.market_tools")

router_market_tools = APIRouter(prefix="/api/tools", tags=["market-tools (Agent Builder)"])


def _check_api_key(x_api_key: Optional[str]) -> None:
    esperado = (os.getenv("MARKET_TOOLS_API_KEY") or "").strip()
    if not esperado:
        raise HTTPException(status_code=503, detail="Market tools sem API key configurada.")
    if (x_api_key or "").strip() != esperado:
        raise HTTPException(status_code=401, detail="API key inválida.")


def _nivel_saturacao(n: int) -> str:
    if n <= 5:
        return "baixo"
    if n <= 12:
        return "medio"
    return "alto"


# ─── /api/tools/concorrentes ──────────────────────────────────────────────────

class ConcorrentesInput(BaseModel):
    cidade: str = Field(min_length=2, max_length=120)
    bairro: str = Field(min_length=2, max_length=120)
    uf: Optional[str] = Field(default=None, max_length=2)
    tipo_negocio: str = Field(default="academia", max_length=40)
    raio_metros: int = Field(default=1500, ge=300, le=5000)


class ConcorrenteItem(BaseModel):
    nome: str
    endereco: Optional[str] = None
    distancia_m: Optional[int] = None
    rating: Optional[float] = None
    avaliacoes: Optional[int] = None


class ConcorrentesResp(BaseModel):
    total_concorrentes: int
    nivel_saturacao: str          # baixo | medio | alto
    concorrentes: list[ConcorrenteItem]


@router_market_tools.post("/concorrentes", response_model=ConcorrentesResp)
async def tool_concorrentes(
    data: ConcorrentesInput,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """Conta e lista academias concorrentes num raio do bairro (Google Maps ao vivo).
    Consumido pelo Agent Builder via OpenAPI tool `buscarConcorrentes`."""
    _check_api_key(x_api_key)
    from tools.competitor_tools import buscar_academias

    try:
        res = await asyncio.to_thread(
            buscar_academias, data.bairro, data.cidade,
            int(data.raio_metros), (data.uf or ""), data.tipo_negocio,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("tool_concorrentes falhou")
        raise HTTPException(status_code=502, detail=f"Falha na busca: {type(e).__name__}") from e

    brutos = res.get("concorrentes") or []
    itens: list[ConcorrenteItem] = []
    for c in brutos:
        if not isinstance(c, dict):
            continue
        itens.append(ConcorrenteItem(
            nome=(c.get("nome") or c.get("name") or c.get("displayName") or "?"),
            endereco=(c.get("endereco") or c.get("address") or c.get("formattedAddress")),
            distancia_m=(c.get("distancia_m") or c.get("distance_m") or c.get("distancia")),
            rating=(c.get("rating") or c.get("nota")),
            avaliacoes=(c.get("num_avaliacoes") or c.get("avaliacoes") or c.get("user_ratings_total")),
        ))

    total = len(itens)
    itens.sort(key=lambda x: x.distancia_m if x.distancia_m is not None else 99_999)
    return ConcorrentesResp(
        total_concorrentes=total,
        nivel_saturacao=_nivel_saturacao(total),
        concorrentes=itens[:8],  # top 8 enxuto; o agente usa o total_concorrentes real
    )


# Montar em api.py:
#   from backend.routers.market_tools import router_market_tools
#   app.include_router(router_market_tools)
