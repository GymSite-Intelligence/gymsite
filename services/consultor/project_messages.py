"""
services/consultor/project_messages.py
========================================
CRUD de mensagens do UserProject no Supabase.

Tabela: project_messages (criada pela migration 20260620_add_user_projects.sql)
"""
from __future__ import annotations

import asyncio
from typing import Any

from services.consultor.project_state import _client
from tools.db_schema import tbl


async def salvar_mensagem(
    projeto_id: str,
    role: str,
    content: str,
    tool_calls: list[dict] | None = None,
    tool_results: list[dict] | None = None,
    tokens_entrada: int | None = None,
    tokens_saida: int | None = None,
) -> str:
    """
    Persiste uma mensagem no projeto.
    Retorna o ID da mensagem criada.
    role: 'user' | 'assistant' | 'system' | 'tool'
    """
    db = _client()
    data: dict[str, Any] = {
        "projeto_id": projeto_id,
        "role": role,
        "content": content,
    }
    if tool_calls is not None:
        data["tool_calls"] = tool_calls
    if tool_results is not None:
        data["tool_results"] = tool_results
    if tokens_entrada is not None:
        data["tokens_entrada"] = tokens_entrada
    if tokens_saida is not None:
        data["tokens_saida"] = tokens_saida

    result = await asyncio.to_thread(
        lambda: tbl(db, "project_messages").insert(data).execute()
    )
    return result.data[0]["id"]


async def carregar_historico(
    projeto_id: str,
    limite: int = 20,
) -> list[dict]:
    """
    Retorna as últimas `limite` mensagens do projeto em ordem cronológica.
    Formato compatível com o loop do consultor_engine.
    """
    db = _client()
    result = await asyncio.to_thread(
        lambda: tbl(db, "project_messages")
            .select("id,role,content,tool_calls,tool_results,created_at")
            .eq("projeto_id", projeto_id)
            .order("created_at", desc=True)
            .limit(limite)
            .execute()
    )
    # Inverte para ordem cronológica (mais antiga primeiro)
    mensagens = list(reversed(result.data or []))
    return mensagens


async def carregar_historico_completo(projeto_id: str) -> list[dict]:
    """
    Retorna TODAS as mensagens do projeto (para a tela de detalhe).
    """
    db = _client()
    result = await asyncio.to_thread(
        lambda: tbl(db, "project_messages")
            .select("*")
            .eq("projeto_id", projeto_id)
            .order("created_at", desc=False)
            .execute()
    )
    return result.data or []
