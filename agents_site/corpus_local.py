"""Deterministic local corpus retrieve — L2 fallback when Eros empty/off."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

Dominio = Literal["mercado", "regulatorio", "engenharia", "tecnico"]

_ROOT = Path(__file__).resolve().parents[1] / "docs" / "agente" / "agentes_site" / "rag"

_GLOBS: dict[Dominio, tuple[str, ...]] = {
    "regulatorio": ("regulatorio_*.txt", "mapa_uf_cref_*.txt"),
    "engenharia": ("engenharia_*.txt",),
    "tecnico": ("tecnico_*.txt",),
    "mercado": ("mercado_*.txt",),
}

_CHUNK = 1200
_OVERLAP = 200


def _tokenize(q: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9à-ü]{3,}", (q or "").lower())}


def _score(chunk: str, tokens: set[str]) -> int:
    low = chunk.lower()
    return sum(1 for t in tokens if t in low)


def buscar_corpus_local(
    pergunta: str, *, dominio: Dominio, n: int = 4
) -> dict:
    tokens = _tokenize(pergunta)
    hits: list[tuple[int, dict]] = []
    if not _ROOT.is_dir():
        return {
            "resultados": [],
            "n_docs": 0,
            "fonte": "corpus_local",
            "status": "indisponivel",
            "aviso_usuario": "Corpus local não encontrado no deploy.",
        }
    for pattern in _GLOBS.get(dominio, ()):
        for path in sorted(_ROOT.glob(pattern)):
            text = path.read_text(encoding="utf-8", errors="replace")
            i = 0
            while i < len(text):
                chunk = text[i : i + _CHUNK]
                sc = _score(chunk, tokens) if tokens else 0
                if sc > 0:
                    hits.append(
                        (
                            sc,
                            {
                                "titulo": path.name,
                                "trecho": chunk.strip()[:800],
                                "uri": str(path.as_posix()),
                                "fonte": f"corpus_local:{path.name}",
                            },
                        )
                    )
                i += _CHUNK - _OVERLAP
    hits.sort(key=lambda x: -x[0])
    seen: set[str] = set()
    resultados: list[dict] = []
    for _, row in hits:
        key = row["titulo"] + row["trecho"][:40]
        if key in seen:
            continue
        seen.add(key)
        resultados.append(row)
        if len(resultados) >= max(1, n):
            break
    return {
        "resultados": resultados,
        "n_docs": len(resultados),
        "fonte": f"corpus_local/{dominio}",
        "status": "ok" if resultados else "vazio",
    }
