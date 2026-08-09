"""
Cron interno — disparado por Supabase pg_cron + pg_net.

Auth: header X-Cron-Secret == env MARKET_BATCH_CRON_SECRET.
Rode no gymsite-worker (RUN_QUEUE_WORKER=1) — batch pode levar dezenas de minutos.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("gymsite.internal_cron")

router_internal_cron = APIRouter(prefix="/api/internal/cron", tags=["internal-cron"])


def _check_cron_secret(x_cron_secret: Optional[str]) -> None:
    esperado = (os.getenv("MARKET_BATCH_CRON_SECRET") or "").strip()
    if not esperado:
        raise HTTPException(
            status_code=503,
            detail="MARKET_BATCH_CRON_SECRET não configurado no serviço.",
        )
    if (x_cron_secret or "").strip() != esperado:
        raise HTTPException(status_code=401, detail="Cron secret inválido.")


class WeeklyBatchBody(BaseModel):
    only_cvm: bool = Field(default=False, description="Só CVM + benchmarks, sem bundles")
    skip_enrichment: bool = Field(
        default=True,
        description="Bundles usam enrichment cache existente (padrão cron)",
    )
    sync: bool = Field(
        default=False,
        description="Bloqueia até terminar (só smoke/teste; cron usa async)",
    )


@router_internal_cron.post("/weekly-market-batch")
async def cron_weekly_market_batch(
    body: WeeklyBatchBody | None = None,
    x_cron_secret: Optional[str] = Header(default=None, alias="X-Cron-Secret"),
):
    """Dispara run_weekly_market_batch (IBGE/CVM/SINAPI → market_bundles Supabase)."""
    _check_cron_secret(x_cron_secret)
    payload = body or WeeklyBatchBody()

    from tools.market_batch_runner import (
        batch_state,
        run_weekly_market_batch,
        start_weekly_market_batch_async,
    )

    if payload.sync:
        import asyncio

        rc = await asyncio.to_thread(
            run_weekly_market_batch,
            skip_enrichment=payload.skip_enrichment,
            only_cvm=payload.only_cvm,
        )
        if rc != 0:
            raise HTTPException(status_code=500, detail=f"weekly batch exit={rc}")
        return {"status": "ok", "mode": "sync", **batch_state()}

    result = start_weekly_market_batch_async(
        skip_enrichment=payload.skip_enrichment,
        only_cvm=payload.only_cvm,
    )
    if result.get("status") == "already_running":
        raise HTTPException(status_code=409, detail=result)
    return result


@router_internal_cron.get("/weekly-market-batch/status")
async def cron_weekly_market_batch_status(
    x_cron_secret: Optional[str] = Header(default=None, alias="X-Cron-Secret"),
):
    """Estado do batch em background (debug ops)."""
    _check_cron_secret(x_cron_secret)
    from tools.market_batch_runner import batch_state

    return batch_state()
