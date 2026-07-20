"""Recuperação de turnos site chat órfãos (user gravado, assistant ausente)."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

from services.consultor.consultor_engine import _ANON_SITE_USER_ID
from tools.db_schema import tbl

logger = logging.getLogger("gymsite.api")

_SITE_CHAT_ORPHAN_MINUTES = int(os.getenv("SITE_CHAT_ORPHAN_MINUTES", "4"))


def _parse_ts(raw: str) -> datetime:
    s = (raw or "").replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


async def recover_stale_site_conversas_async(sb, *, projeto_id: str | None = None) -> int:
    """Reprocessa sessões anon cujo último turno ficou só com msg user (worker morreu)."""
    from agents_site.runner import completar_turno_orfao_site

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=_SITE_CHAT_ORPHAN_MINUTES)
    q = (
        tbl(sb, "user_projects")
        .select("id")
        .eq("user_id", _ANON_SITE_USER_ID)
        .eq("status", "EM_CONVERSA")
    )
    if projeto_id:
        q = q.eq("id", projeto_id)
    rows = await asyncio.to_thread(lambda: q.execute().data or [])

    recovered = 0
    for row in rows:
        pid = row["id"]
        msgs = await asyncio.to_thread(
            lambda p=pid: (
                tbl(sb, "project_messages")
                .select("role, content, created_at")
                .eq("projeto_id", p)
                .order("created_at")
                .execute()
                .data
                or []
            )
        )
        if not msgs or msgs[-1].get("role") != "user":
            continue
        try:
            last_at = _parse_ts(str(msgs[-1]["created_at"]))
        except (TypeError, ValueError):
            continue
        if last_at > cutoff:
            continue
        try:
            ok = await completar_turno_orfao_site(pid, agente="degustacao")
            if ok:
                recovered += 1
                logger.warning("site_conversar órfão recuperado projeto=%s", pid)
        except Exception:
            logger.exception("falha ao recuperar site_conversar órfão projeto=%s", pid)
    return recovered
