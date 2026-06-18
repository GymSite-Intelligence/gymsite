"""Catálogos/taxonomias recalibráveis — DADO em tabela (catalogos_metodologia), não
dict inline no código (regra: todo dado que gera insight é tabelizado e importado).

Espelha tools/parametros_metodologia: tabela Supabase é a fonte viva; _fallback() é o
seed rotulado usado se a tabela não responder. Accessor `catalogo(nome)` + utilitário
`normalizar_servicos()` (texto bruto/marketing → categorias de serviço limpas).
"""
from __future__ import annotations

import os
import re
import unicodedata
from typing import Any

_CACHE: dict[str, list[dict[str, Any]]] = {}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "").lower()).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip()


def _fallback(nome: str) -> list[dict[str, Any]]:
    """Seed rotulado (fallback se a tabela falhar). Reaproveita os dicts existentes —
    enquanto migram, são a fonte do seed; a tabela é a fonte viva."""
    if nome == "servicos":
        try:
            from agents.a9_positioning_strategist import _SERVICOS_CATALOGO
            from tools.competitor_offer_mapper import MODALIDADES_KEYWORDS

            return [
                {"chave": k, "valor": v, "sinonimos": MODALIDADES_KEYWORDS.get(k, [])}
                for k, v in _SERVICOS_CATALOGO.items()
            ]
        except Exception:
            return []
    return []


def catalogo(nome: str) -> list[dict[str, Any]]:
    """[{chave, valor, sinonimos}] do catálogo. Supabase (catalogos_metodologia) primeiro,
    _fallback() rotulado se indisponível. Cacheado por processo."""
    if nome in _CACHE:
        return _CACHE[nome]
    rows: list[dict[str, Any]] = []
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_SERVICE_KEY")
           or os.environ.get("SUPABASE_KEY"))
    if os.environ.get("SUPABASE_URL") and key:
        try:
            from tools.supabase_client import load_create_client

            cli = load_create_client()(os.environ["SUPABASE_URL"], key)
            res = cli.table("catalogos_metodologia").select(
                "chave,valor,sinonimos").eq("catalogo", nome).execute()
            rows = [r for r in (getattr(res, "data", None) or []) if r.get("valor")]
        except Exception as e:
            print(f"[catalogos] Supabase indisponível ({nome}): {type(e).__name__}: {e}")
    if not rows:
        rows = _fallback(nome)
    _CACHE[nome] = rows
    return rows


def normalizar_servicos(textos) -> list[str]:
    """Texto(s) bruto(s) de plano/oferta (marketing) → categorias de serviço LIMPAS
    (labels do catálogo 'servicos'), via match de sinônimos. Sem prosa de marketing."""
    if isinstance(textos, str):
        textos = [textos]
    blob = _norm(" ".join(str(t) for t in (textos or [])))
    if not blob:
        return []
    out: list[str] = []
    for c in catalogo("servicos"):
        chaves = list(c.get("sinonimos") or []) + [c.get("chave", "")]
        if any(_norm(k) and _norm(k) in blob for k in chaves):
            label = c.get("valor")
            if label and label not in out:
                out.append(label)
    return out
