# tools/redis_pubsub.py — Pub/Sub para notificações realtime
"""
Publica eventos quando relatórios ficam prontos.
Frontend pode consumir via SSE ou polling.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from tools.redis_client import get_redis

logger = logging.getLogger("gymsite.api")
CHANNEL = "gymsite:events"


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
