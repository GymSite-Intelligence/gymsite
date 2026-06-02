"""
Executa A8 pós-A6 e persiste em `validacoes` (fail-safe).
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import threading
import time
from typing import Any, Optional

logger = logging.getLogger("gymsite.a8")

_UUID_RE = (
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)

_A8_TIMEOUT_SEC = int(os.getenv("A8_VALIDATION_TIMEOUT_SEC", "120"))


def _supabase_client():
    """Cliente service-role; None se env ausente ou pacote indisponível."""
    from supabase import create_client  # type: ignore[reportAttributeAccessIssue]

    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        return None
    return create_client(url, key)


def a8_habilitado() -> bool:
    return os.getenv("A8_VALIDATOR_ENABLED", "1").lower() not in ("0", "false", "no")


def _resolve_relatorio_uuid(sb, relatorio_id: str) -> str | None:
    """UUID Supabase a partir de UUID ou adk_run_id (`rpt_*`)."""
    rid = (relatorio_id or "").strip()
    if not rid:
        return None
    if re.match(_UUID_RE, rid, re.I):
        return rid
    if rid.startswith("rpt_"):
        res = (
            sb.table("relatorios")
            .select("id")
            .eq("adk_run_id", rid)
            .maybe_single()
            .execute()
        )
        if res.data:
            return str(res.data["id"])
    return None


async def run_a8_validation_async(
    relatorio_markdown: str,
    state: dict[str, Any],
    *,
    relatorio: dict[str, Any] | None = None,
    custo_brl: Optional[float] = None,
) -> Optional[dict[str, Any]]:
    if not a8_habilitado():
        logger.debug("A8 desabilitado via env var", extra={"agent": "A8"})
        return None

    start = time.perf_counter()
    try:
        from agents.a8_validator import A8ValidadorCruzado

        validador = A8ValidadorCruzado()
        result = await validador.validar(
            relatorio_markdown,
            state,
            relatorio=relatorio,
            custo_brl=custo_brl,
        )
        elapsed = time.perf_counter() - start
        logger.info(
            "A8 validation completed in %.2fs | status=%s | claims=%d",
            elapsed,
            result.get("status_validacao") if result else "NONE",
            result.get("claims_verificadas", 0) if result else 0,
            extra={"agent": "A8"},
        )
        return result
    except Exception as e:
        elapsed = time.perf_counter() - start
        logger.error(
            "A8 validation falhou após %.2fs: %s",
            elapsed,
            e,
            exc_info=True,
            extra={"agent": "A8"},
        )
        return None


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
                    ),
                )
                return future.result(timeout=_A8_TIMEOUT_SEC)
        return asyncio.run(
            run_a8_validation_async(
                relatorio_markdown,
                state,
                relatorio=relatorio,
                custo_brl=custo_brl,
            )
        )
    except Exception as e:
        logger.warning(
            "A8 run_a8_validation falhou: %s",
            e,
            exc_info=True,
            extra={"agent": "A8"},
        )
        return None


def _persist_validacao_sync(
    relatorio_id: str,
    org_id: str,
    validacao: dict[str, Any],
) -> None:
    """INSERT síncrono em validacoes (service role)."""
    try:
        sb = _supabase_client()
        if sb is None:
            logger.warning(
                "A8 persist: SUPABASE_URL ou KEY ausentes",
                extra={"agent": "A8"},
            )
            return
        rel_uuid = _resolve_relatorio_uuid(sb, relatorio_id)
        if not rel_uuid:
            logger.warning(
                "A8 persist: relatorio_id inválido ou não encontrado no Supabase: %s",
                relatorio_id,
                extra={"agent": "A8"},
            )
            return

        row = {
            "relatorio_id": rel_uuid,
            "org_id": org_id,
            "validacao_id": validacao.get("validacao_id") or f"val_{rel_uuid[:8]}",
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
        logger.info(
            "A8 persist_validacao OK rel=%s",
            rel_uuid,
            extra={"agent": "A8"},
        )
    except Exception as e:
        logger.warning(
            "A8 persist_validacao falhou rel=%s: %s",
            relatorio_id,
            e,
            exc_info=True,
            extra={"agent": "A8"},
        )


def persist_validacao(
    relatorio_id: str,
    org_id: str,
    validacao: dict[str, Any],
) -> bool:
    """Enfileira persistência em background thread. Retorna imediatamente."""
    if not relatorio_id or not validacao:
        return False
    try:
        t = threading.Thread(
            target=_persist_validacao_sync,
            args=(relatorio_id, org_id, validacao),
            daemon=True,
            name="a8-persist",
        )
        t.start()
        return True
    except Exception as e:
        logger.warning(
            "A8 failed to spawn persist thread: %s",
            e,
            exc_info=True,
            extra={"agent": "A8"},
        )
        return False
