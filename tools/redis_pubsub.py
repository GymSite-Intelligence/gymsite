# tools/redis_pubsub.py — Pub/Sub para notificações realtime + progresso pipeline (ADR-006)
"""
Publica eventos quando relatórios ficam prontos e progresso por agente.
Frontend consome via WS/SSE ou polling.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from tools.redis_client import get_redis

logger = logging.getLogger("gymsite.api")
CHANNEL = "gymsite:events"
PIPELINE_CHANNEL_PREFIX = "gymsite:pipeline:"
PIPELINE_STATE_PREFIX = "gymsite:pipeline:state:"
PIPELINE_STATE_TTL_SEC = 3600
EVENT_VERSION = 1


def pipeline_channel(relatorio_id: str) -> str:
    return f"{PIPELINE_CHANNEL_PREFIX}{relatorio_id}"


def pipeline_state_key(relatorio_id: str) -> str:
    return f"{PIPELINE_STATE_PREFIX}{relatorio_id}"


def _sync_redis():
    """Cliente sync curto pra callbacks ADK (sync) — não usa o pool async."""
    import redis as redis_sync

    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return redis_sync.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=1.5,
        socket_timeout=2.0,
    )


def _progress_event(
    *,
    relatorio_id: str,
    agent_id: str,
    status: str,
    tokens: int = 0,
    latency_ms: int = 0,
) -> dict[str, Any]:
    return {
        "v": EVENT_VERSION,
        "type": "agent.progress",
        "relatorio_id": relatorio_id,
        "agent_id": agent_id,
        "status": status,
        "tokens": int(tokens or 0),
        "latency_ms": int(latency_ms or 0),
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def publish_pipeline_progress_sync(
    *,
    relatorio_id: str,
    agent_id: str,
    status: str,
    tokens: int = 0,
    latency_ms: int = 0,
) -> None:
    """Best-effort sync (ADR-006). Falha de Redis NÃO derruba o pipeline."""
    if not relatorio_id or not agent_id:
        return
    event = _progress_event(
        relatorio_id=relatorio_id,
        agent_id=agent_id,
        status=status,
        tokens=tokens,
        latency_ms=latency_ms,
    )
    client = None
    try:
        client = _sync_redis()
        payload = json.dumps(event, ensure_ascii=False)
        client.publish(pipeline_channel(relatorio_id), payload)
        # Espelho no canal legado pra consumidores genéricos
        client.publish(CHANNEL, json.dumps({"type": "agent.progress", "payload": event}))
        key = pipeline_state_key(relatorio_id)
        client.hset(
            key,
            agent_id,
            json.dumps(
                {
                    "status": status,
                    "tokens": event["tokens"],
                    "latency_ms": event["latency_ms"],
                    "ts": event["ts"],
                },
                ensure_ascii=False,
            ),
        )
        client.expire(key, PIPELINE_STATE_TTL_SEC)
    except Exception as e:
        logger.warning("publish_pipeline_progress_sync failed: %s", e)
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


async def publish_event(event_type: str, payload: dict[str, Any]) -> None:
    """Publica evento no canal Redis."""
    try:
        r = await get_redis()
        message = json.dumps({"type": event_type, "payload": payload})
        await r.publish(CHANNEL, message)
    except Exception as e:
        logger.warning(f"Failed to publish event: {e}")


async def notify_relatorio_pronto(relatorio_id: str, cidade: str, status: str = "done") -> None:
    """Notifica que um relatório ficou pronto."""
    await publish_event("relatorio.pronto", {
        "relatorio_id": relatorio_id,
        "cidade": cidade,
        "status": status,
        "url": f"/api/relatorios/{relatorio_id}",
    })


async def notify_prospeccao_pronta(cidade: str, oportunidades_count: int) -> None:
    """Notifica que uma prospecção foi concluída."""
    await publish_event("prospeccao.pronta", {
        "cidade": cidade,
        "oportunidades_count": oportunidades_count,
    })


async def publish_pipeline_progress(
    *,
    relatorio_id: str,
    agent_id: str,
    status: str,
    tokens: int = 0,
    latency_ms: int = 0,
) -> None:
    """Versão async do progresso (mesma semântica do sync)."""
    if not relatorio_id or not agent_id:
        return
    event = _progress_event(
        relatorio_id=relatorio_id,
        agent_id=agent_id,
        status=status,
        tokens=tokens,
        latency_ms=latency_ms,
    )
    try:
        r = await get_redis()
        payload = json.dumps(event, ensure_ascii=False)
        await r.publish(pipeline_channel(relatorio_id), payload)
        await r.publish(CHANNEL, json.dumps({"type": "agent.progress", "payload": event}))
        key = pipeline_state_key(relatorio_id)
        await r.hset(
            key,
            agent_id,
            json.dumps(
                {
                    "status": status,
                    "tokens": event["tokens"],
                    "latency_ms": event["latency_ms"],
                    "ts": event["ts"],
                },
                ensure_ascii=False,
            ),
        )
        await r.expire(key, PIPELINE_STATE_TTL_SEC)
    except Exception as e:
        logger.warning("publish_pipeline_progress failed: %s", e)


async def get_pipeline_snapshot(relatorio_id: str) -> dict[str, Any]:
    """Lê hash de snapshot; {} se Redis/chave ausente."""
    if not relatorio_id:
        return {}
    try:
        r = await get_redis()
        raw = await r.hgetall(pipeline_state_key(relatorio_id))
        out: dict[str, Any] = {}
        for agent_id, blob in (raw or {}).items():
            try:
                out[agent_id] = json.loads(blob) if isinstance(blob, str) else blob
            except Exception:
                out[agent_id] = {"raw": blob}
        return out
    except Exception as e:
        logger.warning("get_pipeline_snapshot failed: %s", e)
        return {}
