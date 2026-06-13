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


# Benchmarks setoriais fixos — fontes públicas do setor. Permite responder
# perguntas genéricas ("freq. semanal por modelo?") sem depender de relatório.
_BENCHMARKS_SETOR = """--- BENCHMARKS DO SETOR (referência geral, fontes públicas) ---
Frequência semanal por aluno (IHRSA / ACAD Brasil):
- Low cost / high volume: 1,8–2,2x por semana
- Mid market: 2,0–2,5x por semana
- Premium / boutique: 2,5–3,0x por semana
Ticket mensal típico Brasil (CVM SMFT3 + planos públicos das redes):
- Low cost: R$ 90–160 (ARPU Smart Fit ~R$ 140, CVM)
- Mid market: R$ 150–280
- Premium: R$ 300–700
Churn mensal típico: 5–8% (low cost no teto, premium no piso).
Cite a fonte ao usar esses números."""


def _v(d: dict, chave: str) -> str:
    """`.get(chave, 'N/A')` não cobre valor None vindo do banco — None virava
    o literal "None" no prompt e o modelo ecoava pro usuário."""
    valor = d.get(chave)
    return str(valor) if valor not in (None, "") else "N/A"


def build_contexto_chat(
    user_id: str,
    pergunta: str,
    relatorio_id: str | None = None,
    meta: dict | None = None,
) -> str:
    """Monta o contexto em texto para injetar no prompt do Tinker Bot.

    Args:
        user_id: UUID do usuário autenticado.
        pergunta: Pergunta atual do usuário.
        relatorio_id: Opcional — se o usuário está perguntando sobre um relatório específico.
        meta: Opcional — dict que a função preenche com `kb_fontes` (chunks RAG
            usados) pro caller logar em chat_interacoes sem refazer a busca.
    """
    partes: list[str] = []
    partes.append("Você é o GymSite Assistant, um especialista em viabilidade de franquias de academia no Brasil.")
    partes.append("Responda de forma clara, objetiva e em português.")
    partes.append("")
    partes.append(_BENCHMARKS_SETOR)
    partes.append("")

    # RAG kb_chunks (franquias, mercado): top-k por similaridade; falha → segue sem
    try:
        from services.kb_rag import buscar_kb, formatar_contexto_kb

        chunks_kb = buscar_kb(pergunta)
        if meta is not None:
            meta["kb_fontes"] = [
                {"fonte": c.get("fonte"), "titulo": c.get("titulo"),
                 "similarity": c.get("similarity"), "ano": c.get("ano_referencia")}
                for c in chunks_kb
            ]
        bloco_kb = formatar_contexto_kb(chunks_kb)
        if bloco_kb:
            partes.append(bloco_kb)
            partes.append("")
    except Exception:
        pass

    if relatorio_id:
        rel = buscar_relatorio_por_id(relatorio_id)
        if rel:
            inputs = _fmt_inputs(rel)
            outputs = _fmt_outputs(rel)
            partes.append("--- RELATÓRIO EM FOCO ---")
            partes.append(f"Cidade: {_v(inputs, 'cidade')}")
            partes.append(f"Bairro: {_v(inputs, 'bairro')}")
            partes.append(f"Veredito: {_v(outputs, 'veredito')}")
            partes.append(f"Resumo: {_v(outputs, 'resumo_executivo')}")
            partes.append("")
    else:
        relatorios = buscar_relatorios_usuario(user_id, limit=3)
        if relatorios:
            partes.append("--- RELATÓRIOS RECENTES DO USUÁRIO ---")
            for r in relatorios:
                inputs = _fmt_inputs(r)
                outputs = _fmt_outputs(r)
                partes.append(
                    f"- {_v(inputs, 'cidade')}/{_v(inputs, 'bairro')} | "
                    f"Veredito: {_v(outputs, 'veredito')} | Status: {_v(r, 'status')}"
                )
            partes.append("")

    partes.append("--- PERGUNTA DO USUÁRIO ---")
    partes.append(pergunta)
    partes.append("")
    partes.append(
        "Regras de resposta: NUNCA repita os rótulos/estrutura do contexto acima "
        "(o usuário não vê este texto). Pergunta geral do setor → responda com os "
        "benchmarks acima, citando fonte. Pergunta sobre relatório → use os dados "
        "do relatório. Campo N/A → simplesmente não o mencione. Sem o dado → diga "
        "o que falta em linguagem natural, sem citar nomes de campos."
    )

    return "\n".join(partes)
