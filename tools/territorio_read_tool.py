"""
R2 — Leitura do territorio (sintese do heatmap via Gemini).

Recebe um RESUMO AGREGADO do recorte visivel do mapa (cidade, bbox, contagens
por oceano, top bairros e vereditos) e devolve uma leitura curta de negocio em
JSON estruturado: {titulo, leitura, recomendacao, confianca}.

Principios:
- Defensivo: nunca levanta excecao para o chamador; em erro/timeout retorna um
  fallback estatico ("Leitura indisponivel no momento").
- Anti-alucinacao: o prompt usa SOMENTE o resumo fornecido e o JSON Schema
  obriga o formato de saida.
- Custo: cache em memoria por hash do resumo (TTL curto) evita repagar a mesma
  vista; o endpoint/front aplicam debounce.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

_MODEL = "gemini-2.5-flash"

# Cache em processo: hash(resumo) -> (expira_em_epoch, payload)
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_TTL_SEC = 3600  # 1h (vista costuma se repetir em pan/zoom)
_CACHE_MAX = 256

_CONFIANCA_VALIDA = {"alta", "media", "baixa"}

_FALLBACK: dict[str, Any] = {
    "titulo": "Leitura indisponivel",
    "leitura": "Leitura indisponivel no momento.",
    "recomendacao": "Tente novamente em instantes.",
    "confianca": "baixa",
}


def _hash_resumo(resumo: dict[str, Any]) -> str:
    try:
        canon = json.dumps(resumo, sort_keys=True, ensure_ascii=False, default=str)
    except Exception:
        canon = repr(resumo)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _cache_get(chave: str) -> dict[str, Any] | None:
    item = _CACHE.get(chave)
    if not item:
        return None
    expira_em, payload = item
    if time.time() >= expira_em:
        _CACHE.pop(chave, None)
        return None
    return payload


def _cache_set(chave: str, payload: dict[str, Any]) -> None:
    if len(_CACHE) >= _CACHE_MAX:
        # remove o item mais proximo de expirar (limpeza simples)
        try:
            mais_velho = min(_CACHE.items(), key=lambda kv: kv[1][0])[0]
            _CACHE.pop(mais_velho, None)
        except ValueError:
            pass
    _CACHE[chave] = (time.time() + _CACHE_TTL_SEC, payload)


def _prompt(resumo: dict[str, Any]) -> str:
    bloco = json.dumps(resumo, ensure_ascii=False, indent=2, default=str)
    return (
        "Voce e um analista de expansao de mercado para academias. "
        "Abaixo esta um RESUMO AGREGADO do recorte VISIVEL de um mapa de "
        "saturacao (heatmap) — contagens por oceano (vermelho=saturado, "
        "transicao, azul=oportunidade), top bairros e vereditos.\n"
        "Escreva uma leitura curta de negocio usando SOMENTE estes dados. "
        "NAO invente bairros, numeros ou areas que nao estejam no resumo. "
        "Cite cada entidade pelo nome completo na primeira mencao.\n\n"
        f"RESUMO DO RECORTE:\n{bloco}\n\n"
        "Responda APENAS com o JSON do schema (titulo, leitura, "
        "recomendacao, confianca)."
    )


def _schema(types: Any) -> Any:
    return types.Schema(
        type=types.Type.OBJECT,
        required=["titulo", "leitura", "recomendacao", "confianca"],
        properties={
            "titulo": types.Schema(type=types.Type.STRING),
            "leitura": types.Schema(type=types.Type.STRING),
            "recomendacao": types.Schema(type=types.Type.STRING),
            "confianca": types.Schema(
                type=types.Type.STRING,
                enum=["alta", "media", "baixa"],
            ),
        },
    )


def _normalizar(bruto: Any) -> dict[str, Any]:
    """Valida/sanitiza a saida do modelo; cai no fallback se faltar campo."""
    if not isinstance(bruto, dict):
        return dict(_FALLBACK)
    out: dict[str, Any] = {}
    out["titulo"] = str(bruto.get("titulo") or "").strip() or _FALLBACK["titulo"]
    out["leitura"] = str(bruto.get("leitura") or "").strip() or _FALLBACK["leitura"]
    out["recomendacao"] = (
        str(bruto.get("recomendacao") or "").strip() or _FALLBACK["recomendacao"]
    )
    conf = str(bruto.get("confianca") or "").strip().lower()
    out["confianca"] = conf if conf in _CONFIANCA_VALIDA else "baixa"
    return out


def ler_territorio(resumo: dict[str, Any]) -> dict[str, Any]:
    """Gera a leitura do territorio a partir do resumo agregado do recorte.

    Sempre retorna um dict no formato {titulo, leitura, recomendacao, confianca}.
    Nunca levanta excecao (retorna fallback em qualquer falha).
    """
    if not isinstance(resumo, dict) or not resumo:
        return dict(_FALLBACK)

    chave = _hash_resumo(resumo)
    cacheado = _cache_get(chave)
    if cacheado is not None:
        return cacheado

    try:
        from google.genai import types
        from tools._genai_client import build_genai_client, generate_content_resilient

        client = build_genai_client()
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=_schema(types),
            temperature=0.2,
        )
        resp = generate_content_resilient(
            client,
            model=_MODEL,
            contents=_prompt(resumo),
            config=config,
        )
        texto = (getattr(resp, "text", "") or "").strip()
        if not texto:
            return dict(_FALLBACK)
        bruto = json.loads(texto)
        payload = _normalizar(bruto)
        _cache_set(chave, payload)
        return payload
    except Exception:
        # Defensivo: rede, billing, quota, JSON invalido -> fallback estatico.
        return dict(_FALLBACK)
