"""Chat State — persistência de sessões conversacionais no Supabase.

Gerencia o estado de slot-filling do Agente de IA Especialista em Fitness.
"""
from __future__ import annotations

import json
import os
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()


def _supabase():
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise RuntimeError("Supabase não configurado")
    return create_client(url, key)


class ChatSession:
    def __init__(self, data: dict[str, Any]) -> None:
        self.id: str = data.get("id", "")
        self.user_id: str = data.get("user_id", "")
        self.intencao: str | None = data.get("intencao")
        self.slots: dict[str, Any] = data.get("slots") or {}
        self.relatorio_id: str | None = data.get("relatorio_id")
        self.status: str = data.get("status", "coletando_slots")
        self.messages: list[dict[str, Any]] = data.get("messages") or []
        self.created_at: str = data.get("created_at", "")
        self.updated_at: str = data.get("updated_at", "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "intencao": self.intencao,
            "slots": self.slots,
            "relatorio_id": self.relatorio_id,
            "status": self.status,
            "messages": self.messages,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ── CRUD ───────────────────────────────────────────────────────────────────


def criar_sessao(user_id: str) -> ChatSession:
    sb = _supabase()
    res = (
        sb.table("sessions")
        .insert({"user_id": user_id, "slots": {}, "messages": []})
        .execute()
    )
    data = res.data[0] if res.data else {}
    return ChatSession(data)


def buscar_sessao(session_id: str) -> ChatSession | None:
    sb = _supabase()
    res = (
        sb.table("sessions")
        .select("*")
        .eq("id", session_id)
        .maybe_single()
        .execute()
    )
    if res.data:
        return ChatSession(res.data)
    return None


def buscar_ultima_sessao_ativa(user_id: str) -> ChatSession | None:
    """Retorna a sessão mais recente do usuário que ainda não está encerrada."""
    sb = _supabase()
    res = (
        sb.table("sessions")
        .select("*")
        .eq("user_id", user_id)
        .neq("status", "encerrado")
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )
    if res.data:
        return ChatSession(res.data[0])
    return None


def atualizar_sessao(
    session_id: str,
    *,
    intencao: str | None = None,
    slots: dict[str, Any] | None = None,
    relatorio_id: str | None = None,
    status: str | None = None,
    messages: list[dict[str, Any]] | None = None,
) -> ChatSession:
    sb = _supabase()
    update: dict[str, Any] = {}
    if intencao is not None:
        update["intencao"] = intencao
    if slots is not None:
        update["slots"] = slots
    if relatorio_id is not None:
        update["relatorio_id"] = relatorio_id
    if status is not None:
        update["status"] = status
    if messages is not None:
        update["messages"] = messages

    res = (
        sb.table("sessions")
        .update(update)
        .eq("id", session_id)
        .execute()
    )
    data = res.data[0] if res.data else {}
    return ChatSession(data)


def adicionar_mensagem(session_id: str, role: str, content: str) -> None:
    sb = _supabase()
    sessao = buscar_sessao(session_id)
    if not sessao:
        return
    messages = list(sessao.messages)
    messages.append({
        "id": str(uuid4()),
        "role": role,
        "content": content,
        "timestamp": "now()",
    })
    sb.table("sessions").update({"messages": messages}).eq("id", session_id).execute()
