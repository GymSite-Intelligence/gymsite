from __future__ import annotations

import re
from typing import Any

from tools.gemini_search_grounding import _executar_grounding_sync

_URL_RE = re.compile(r"https?://[^\s\)\]\"'<>]+", re.I)


def _extrair_fontes(texto: str) -> list[str]:
    fontes: list[str] = []
    for match in _URL_RE.findall(texto or ""):
        url = match.rstrip(".,;)")
        if url not in fontes:
            fontes.append(url)
    return fontes[:20]


def _montar_query(pergunta: str, cidade: str | None, bairro: str | None) -> str:
    local_parts = [part for part in (bairro, cidade) if part]
    local = ", ".join(local_parts)
    if local:
        return (
            f"{pergunta.strip()}\n\n"
            f"Contexto: mercado fitness em {local}, Brasil.\n"
            "Responda em português, com dados públicos recentes e cite fontes URL."
        )
    return (
        f"{pergunta.strip()}\n\n"
        "Contexto: mercado fitness no Brasil.\n"
        "Responda em português, com dados públicos recentes e cite fontes URL."
    )


def responder_pergunta_mercado(
    *,
    pergunta: str,
    cidade: str | None = None,
    bairro: str | None = None,
) -> dict[str, Any]:
    query = _montar_query(pergunta, cidade, bairro)
    cache_key = f"chat_pesquisa_mercado:{bairro or ''}:{cidade or ''}:{pergunta[:120]}".lower()
    texto = _executar_grounding_sync(query, cache_key)
    if texto.startswith("[Search Grounding indisponível") or texto.startswith("[Erro"):
        raise RuntimeError(texto)
    return {
        "resposta": texto.strip(),
        "fontes": _extrair_fontes(texto),
    }
