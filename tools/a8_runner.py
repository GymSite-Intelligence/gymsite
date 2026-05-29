"""
Executa A8 pós-A6 e persiste em `validacoes` (fail-safe).
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Optional

logger = logging.getLogger("gymsite.a8")


def a8_habilitado() -> bool:
    return os.getenv("A8_VALIDATOR_ENABLED", "1").lower() not in ("0", "false", "no")


async def run_a8_validation_async(
    relatorio_markdown: str,
    state: dict[str, Any],
    *,
    relatorio: dict[str, Any] | None = None,
    custo_brl: Optional[float] = None,
) -> Optional[dict[str, Any]]:
    if not a8_habilitado():
        return None
    from agents.a8_validator import A8ValidadorCruzado

    validador = A8ValidadorCruzado()
    return await validador.validar(
        relatorio_markdown,
        state,
        relatorio=relatorio,
        custo_brl=custo_brl,
    )


def run_a8_validation(
    relatorio_markdown: str,
    state: dict[str, Any],
    *,
    relatorio: dict[str, Any] | None = None,
    custo_brl: Optional[float] = None,
) -> Optional[dict[str, Any]]:
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    asyncio.run,
                    run_a8_validation_async(
                        relatorio_markdown,
                        state,
                        relatorio=relatorio,
                        custo_brl=custo_brl,
                    )
                )
                return future.result()
        else:
            return asyncio.run(
                run_a8_validation_async(
                    relatorio_markdown,
                    state,
                    relatorio=relatorio,
                    custo_brl=custo_brl,
                )
            )
    except Exception as e:
        logger.warning("A8 falhou: %s", e)
        return None


def persist_validacao(
    relatorio_id: str,
    org_id: str,
    validacao: dict[str, Any],
) -> bool:
    """INSERT em validacoes. Retorna False se falhar (não bloqueia pipeline)."""
    try:
        url = os.getenv("SUPABASE_URL", "").strip()
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        if not url or not key:
            return False
        from supabase import create_client

        sb = create_client(url, key)
        row = {
            "relatorio_id": relatorio_id,
            "org_id": org_id,
            "validacao_id": validacao.get("validacao_id") or f"val_{relatorio_id[:8]}",
            "status_validacao": validacao.get("status_validacao") or "APROVADO_MINOR_ISSUES",
            "score_validacao": validacao.get("score_validacao") or 0,
            "alertas": validacao.get("alertas") or [],
            "claims_verificadas": validacao.get("claims_verificadas") or 0,
            "claims_com_alertas": validacao.get("claims_com_alertas") or 0,
            "fontes_independentes": validacao.get("fontes_independentes") or [],
            "resumo_executivo_validacao": (
                validacao.get("resumo_executivo_validacao") or ""
            )[:4000],
            "revisar_manual": bool(validacao.get("revisar_manual")),
            "payload": validacao,
        }
        sb.table("validacoes").insert(row).execute()
        return True
    except Exception as e:
        logger.warning("persist validacao falhou rel=%s: %s", relatorio_id, e)
        return False
