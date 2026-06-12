"""
RAG da base de conhecimento (kb_chunks) pro chat assistente.

Fluxo: embed da pergunta via gemini-embedding-001 (Vertex) → match_kb_chunks
(pgvector cosine, HNSW) → chunks com fonte/ano pra citação no prompt.

Ingestão é offline (scripts/batch/ingest_kb.py) — aqui só leitura.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

logger = logging.getLogger("gymsite.kb_rag")

_EMBED_MODEL = os.getenv("KB_EMBED_MODEL", "gemini-embedding-001")
_EMBED_DIM = 768  # precisa bater com vector(768) da migration kb_chunks_rag_chat


@lru_cache(maxsize=1)
def _genai_client():
    from google import genai

    # Mesmo roteamento do pipeline: Vertex estrito (api.py remove GOOGLE_API_KEY)
    return genai.Client(
        vertexai=True,
        project=os.getenv("GOOGLE_CLOUD_PROJECT"),
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "global"),
    )


def embed_texto(texto: str, *, task_type: str = "RETRIEVAL_QUERY") -> list[float] | None:
    """Embedding 768d. task_type: RETRIEVAL_QUERY (pergunta) | RETRIEVAL_DOCUMENT (ingestão)."""
    try:
        from google.genai import types

        resp = _genai_client().models.embed_content(
            model=_EMBED_MODEL,
            contents=texto[:8000],
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=_EMBED_DIM,
            ),
        )
        emb = resp.embeddings[0].values if resp.embeddings else None
        return list(emb) if emb else None
    except Exception as exc:
        logger.warning("embed falhou: %s", exc)
        return None


def buscar_kb(pergunta: str, *, top_k: int = 4, min_similarity: float = 0.62) -> list[dict[str, Any]]:
    # 0.62 calibrado no teste de 12/06: on-topic fica 0.66-0.79, off-topic 0.58.
    """Top-k chunks relevantes. Lista vazia em qualquer falha — chat degrada sem RAG."""
    emb = embed_texto(pergunta, task_type="RETRIEVAL_QUERY")
    if not emb:
        return []
    try:
        from db.supabase_writer import _get_client  # client service_role já configurado

        client = _get_client()
        if client is None:
            return []
        resp = client.rpc(
            "match_kb_chunks",
            {"query_embedding": emb, "match_count": top_k, "min_similarity": min_similarity},
        ).execute()
        return list(resp.data or [])
    except Exception as exc:
        logger.warning("busca kb falhou: %s", exc)
        return []


def formatar_contexto_kb(chunks: list[dict[str, Any]]) -> str:
    """Bloco de contexto com citação obrigatória de fonte + ano (anti-alucinação)."""
    if not chunks:
        return ""
    partes = ["## BASE DE CONHECIMENTO (use APENAS se relevante; cite fonte e ano)"]
    for c in chunks:
        ano = f", {c['ano_referencia']}" if c.get("ano_referencia") else ""
        titulo = c.get("titulo") or c.get("fonte") or "fonte interna"
        partes.append(f"### [{titulo}{ano}]\n{(c.get('conteudo') or '').strip()}")
    partes.append(
        "REGRA: dados acima têm ano de referência — sinalize quando o dado for antigo. "
        "Se a pergunta não relaciona com os trechos, ignore-os por completo."
    )
    return "\n\n".join(partes)
