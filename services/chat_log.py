"""
Log de interações do chat assistente → chat_interacoes (Supabase).

Matéria-prima do dataset de fine-tuning Vertex SFT: cada pergunta/resposta
vira candidata a exemplo de treino; feedback (+1/-1) e correção manual
definem o que entra no JSONL (scripts/batch/export_ft_dataset.py).

Tudo failsafe: falha de log NUNCA derruba a resposta do chat.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("gymsite.chat_log")


def registrar_interacao(
    *,
    user_id: str,
    endpoint: str,
    pergunta: str,
    resposta: str,
    intencao: str | None = None,
    session_id: str | None = None,
    kb_fontes: list[dict[str, Any]] | None = None,
    relatorio_id: str | None = None,
    modelo: str | None = None,
) -> str | None:
    """Insere interação; retorna id (pro frontend referenciar no feedback)."""
    try:
        from db.supabase_writer import _get_client

        client = _get_client()
        if client is None:
            return None
        row = {
            "user_id": user_id,
            "endpoint": endpoint,
            "pergunta": pergunta[:8000],
            "resposta": resposta[:16000],
            "intencao": intencao,
            "session_id": session_id,
            "kb_fontes": kb_fontes or [],
            "relatorio_id": relatorio_id,
            "modelo": modelo,
        }
        res = client.table("chat_interacoes").insert(row).execute()
        return (res.data or [{}])[0].get("id")
    except Exception as exc:
        logger.warning("log de interacao falhou: %s", exc)
        return None


def registrar_feedback(
    interacao_id: str,
    *,
    user_id: str,
    rating: int,
    comentario: str | None = None,
    correcao: str | None = None,
) -> bool:
    """Grava feedback. user_id confere dono — não deixa avaliar interação alheia."""
    if rating not in (-1, 1):
        return False
    try:
        from db.supabase_writer import _get_client

        client = _get_client()
        if client is None:
            return False
        res = (
            client.table("chat_interacoes")
            .update({
                "feedback": rating,
                "feedback_comentario": comentario,
                "correcao": correcao,
                "feedback_em": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", interacao_id)
            .eq("user_id", user_id)
            .execute()
        )
        return bool(res.data)
    except Exception as exc:
        logger.warning("feedback falhou: %s", exc)
        return False
