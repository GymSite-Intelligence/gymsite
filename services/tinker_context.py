"""Builder de contexto para o Tinker Bot.

Busca relatórios e dados relevantes do usuário no Supabase para
enriquecer o prompt do assistente conversacional.
"""
from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()


def _supabase():
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise RuntimeError("Supabase não configurado")
    return create_client(url, key)


def buscar_relatorios_usuario(user_id: str, limit: int = 5) -> list[dict[str, Any]]:
    """Retorna os N relatórios mais recentes do usuário (com inputs e outputs)."""
    sb = _supabase()
    res = (
        sb.table("relatorios")
        .select(
            "id, status, created_at, "
            "relatorio_inputs(cidade, bairro), "
            "relatorio_outputs(veredito, resumo_executivo)"
        )
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


def buscar_relatorio_por_id(relatorio_id: str) -> dict[str, Any] | None:
    """Retorna o detalhe completo de um relatório (com inputs e outputs)."""
    sb = _supabase()
    res = (
        sb.table("relatorios")
        .select(
            "*, "
            "relatorio_inputs(cidade, bairro), "
            "relatorio_outputs(veredito, resumo_executivo)"
        )
        .eq("id", relatorio_id)
        .maybe_single()
        .execute()
    )
    return res.data


def _fmt_inputs(row: dict) -> dict:
    """Normaliza os dados nested do Supabase (relatorio_inputs -> cidade/bairro)."""
    inputs = row.get("relatorio_inputs") or {}
    if isinstance(inputs, list):
        inputs = inputs[0] if inputs else {}
    return inputs


def _fmt_outputs(row: dict) -> dict:
    """Normaliza os dados nested do Supabase (relatorio_outputs -> veredito/resumo)."""
    outputs = row.get("relatorio_outputs") or {}
    if isinstance(outputs, list):
        outputs = outputs[0] if outputs else {}
    return outputs


def build_contexto_chat(user_id: str, pergunta: str, relatorio_id: str | None = None) -> str:
    """Monta o contexto em texto para injetar no prompt do Tinker Bot.

    Args:
        user_id: UUID do usuário autenticado.
        pergunta: Pergunta atual do usuário.
        relatorio_id: Opcional — se o usuário está perguntando sobre um relatório específico.
    """
    partes: list[str] = []
    partes.append("Você é o GymSite Assistant, um especialista em viabilidade de franquias de academia no Brasil.")
    partes.append("Responda de forma clara, objetiva e em português.")
    partes.append("")

    if relatorio_id:
        rel = buscar_relatorio_por_id(relatorio_id)
        if rel:
            inputs = _fmt_inputs(rel)
            outputs = _fmt_outputs(rel)
            partes.append("--- RELATÓRIO EM FOCO ---")
            partes.append(f"Cidade: {inputs.get('cidade', 'N/A')}")
            partes.append(f"Bairro: {inputs.get('bairro', 'N/A')}")
            partes.append(f"Veredito: {outputs.get('veredito', 'N/A')}")
            partes.append(f"Resumo: {outputs.get('resumo_executivo', 'N/A')}")
            partes.append("")
    else:
        relatorios = buscar_relatorios_usuario(user_id, limit=3)
        if relatorios:
            partes.append("--- RELATÓRIOS RECENTES DO USUÁRIO ---")
            for r in relatorios:
                inputs = _fmt_inputs(r)
                outputs = _fmt_outputs(r)
                partes.append(
                    f"- {inputs.get('cidade', 'N/A')}/{inputs.get('bairro', 'N/A')} | "
                    f"Veredito: {outputs.get('veredito', 'N/A')} | Status: {r.get('status', 'N/A')}"
                )
            partes.append("")

    partes.append("--- PERGUNTA DO USUÁRIO ---")
    partes.append(pergunta)
    partes.append("")
    partes.append("Responda com base nos dados disponíveis. Se não souber, diga que precisa de mais informações.")

    return "\n".join(partes)
