"""L3.6 — Gemini como proxy de highlights/planos do Instagram.

Extrai planos e preços públicos (Search Grounding + parse determinístico)
e sanitiza anual→mensal (PONTO 99). Fail-soft: nunca derruba o A3b.
"""
from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("gymsite.instagram_highlights_gemini")

_CACHE_DIR = Path(__file__).resolve().parent.parent / "competitor_cache"
_CACHE_TTL_S = 7 * 86400

_KEYWORDS_ANUAL = [
    "anual",
    "12 meses",
    "12x",
    "black friday",
    "promoção anual",
    "promocao anual",
    "contrato anual",
    "fidelidade 12",
    "12 mensalidade",
]

# Mensalidade plausível de academia no BR (fora → suspeito ou anual mal rotulado).
_FAIXA_MENSAL_BRL = (30.0, 800.0)


def eh_url_instagram(url: str | None) -> bool:
    if not url:
        return False
    return "instagram.com/" in str(url).lower()


def _sanitizar_plano(plano: dict, markdown_context: str) -> dict:
    """Detecta anual vs mensal e normaliza `preco_mensal_brl` (PONTO 99 / RN-A3b-13)."""
    nome = str(plano.get("plano") or "").lower()
    preco = float(plano.get("preco_brl") or 0.0)
    contexto = (markdown_context or "").lower()

    sinal_anual_nome = any(kw in nome for kw in _KEYWORDS_ANUAL)
    sinal_anual_contexto = any(kw in contexto for kw in _KEYWORDS_ANUAL) and (
        not nome or nome[:12] in contexto or any(tok in contexto for tok in nome.split()[:3] if len(tok) > 3)
    )
    sinal_preco_alto = preco > _FAIXA_MENSAL_BRL[1]

    out = dict(plano)
    # Critério de aceite: nome com "anual" → ÷12 mesmo abaixo de R$800 (ex.: BF R$500).
    if sinal_anual_nome and preco > 0:
        out["preco_mensal_brl"] = round(preco / 12.0, 2)
        out["periodo"] = "anual"
        out["observacao"] = "valor anual convertido para mensal (÷12)"
    elif sinal_anual_contexto and sinal_preco_alto:
        out["preco_mensal_brl"] = round(preco / 12.0, 2)
        out["periodo"] = "anual"
        out["observacao"] = "valor anual (inferido pelo contexto)"
    elif preco < _FAIXA_MENSAL_BRL[0] or preco > _FAIXA_MENSAL_BRL[1]:
        out["preco_mensal_brl"] = preco
        out["periodo"] = "indeterminado"
        out["observacao"] = (
            f"preço R${preco:.2f} fora da faixa plausível "
            f"R${_FAIXA_MENSAL_BRL[0]:.0f}-R${_FAIXA_MENSAL_BRL[1]:.0f}/mês"
        )
        out["suspeito"] = True
    else:
        out["preco_mensal_brl"] = preco
        out["periodo"] = "mensal"

    return out


def _extrair_precos_do_markdown(markdown: str) -> list[dict]:
    """Extrai menções de preço e sanitiza anual/mensal."""
    if not markdown:
        return []

    padrao = r"([A-Za-zÀ-ÿ0-9\s\-–]+?)[:\-–]?\s*R\$\s*([\d.,]+)"
    matches = re.findall(padrao, markdown)

    precos_brutos: list[dict] = []
    for nome_raw, preco_raw in matches:
        try:
            preco_str = preco_raw.replace(".", "").replace(",", ".")
            # Heurística BR: "1.299,90" já tratado; "500,00" ok; "500.00" anglo → float direto
            if preco_raw.count(",") == 0 and preco_raw.count(".") == 1:
                preco = float(preco_raw)
            else:
                preco = float(preco_str)
            nome = nome_raw.strip(" :-–\t")
            nome = re.sub(r"^[\-\*\d\.\)\s]+", "", nome).strip()
            if nome and preco > 0:
                precos_brutos.append({"plano": nome[:80], "preco_brl": preco})
        except (ValueError, TypeError):
            continue

    seen: set[tuple] = set()
    deduped: list[dict] = []
    for p in precos_brutos:
        nome_l = p["plano"].lower()
        # Exige indício de plano no rótulo (evita "Fortaleza CE: R$ 41,67" de snippet).
        if not any(
            tok in nome_l
            for tok in (
                "plano", "mensal", "anual", "promo", "black", "pass",
                "fit", "gold", "smart", "acess", "mensalidade", "assinatura",
            )
        ):
            continue
        key = (nome_l, round(p["preco_brl"], 2))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(p)

    return [_sanitizar_plano(p, markdown) for p in deduped]


def _faixa_de_planos(planos: list[dict]) -> dict | None:
    mensais = [
        float(p["preco_mensal_brl"])
        for p in planos
        if isinstance(p.get("preco_mensal_brl"), (int, float))
        and not p.get("suspeito")
        and p.get("periodo") in ("mensal", "anual")
    ]
    if not mensais:
        return None
    mensais_sorted = sorted(mensais)
    mid = mensais_sorted[len(mensais_sorted) // 2]
    return {
        "min": round(min(mensais), 2),
        "max": round(max(mensais), 2),
        "mediana": round(mid, 2),
        "fonte": "instagram_highlights_gemini",
    }


def _cache_path(username: str) -> Path:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", (username or "anon").lower())[:80]
    return _CACHE_DIR / f"ig_highlights_gemini_{safe}.json"


def _cache_load(username: str) -> dict | None:
    p = _cache_path(username)
    if not p.exists():
        return None
    if time.time() - p.stat().st_mtime > _CACHE_TTL_S:
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _cache_save(username: str, payload: dict) -> None:
    try:
        _cache_path(username).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def _searchapi_markdown_planos(username: str, nome_hint: str | None = None) -> str:
    """Fallback L3.6: snippets Google via SearchAPI (sem Gemini)."""
    import os

    import requests

    key = (os.getenv("SEARCHAPI_KEY") or "").strip()
    if not key:
        return ""
    handle = (username or "").strip().lstrip("@")
    nome = (nome_hint or handle).strip()
    q = (
        f'"{nome}" (plano OR mensalidade OR "black friday" OR anual) (R$ OR reais) '
        f'(Fortaleza OR @{handle} OR "athletic fortal")'
    )
    try:
        r = requests.get(
            "https://www.searchapi.io/api/v1/search",
            headers={"Authorization": f"Bearer {key}"},
            params={"engine": "google", "q": q, "gl": "br", "hl": "pt-br", "num": 10},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        logger.warning("L3.6 SearchAPI fallback falhou: %s", type(exc).__name__)
        return ""

    linhas = [f"# Planos públicos — {nome} (@{handle})"]
    for res in (data.get("organic_results") or [])[:8]:
        title = str(res.get("title") or "")
        snip = str(res.get("snippet") or "")
        if "R$" in title or "R$" in snip or "plano" in (title + snip).lower():
            linhas.append(f"- {title}: {snip}")
    # Knowledge / answer box se existir
    for box_key in ("answer_box", "knowledge_graph"):
        box = data.get(box_key)
        if isinstance(box, dict):
            for k, v in box.items():
                if isinstance(v, str) and "R$" in v:
                    linhas.append(f"- {k}: {v}")
    return "\n".join(linhas)


def _gemini_markdown_planos(username: str, nome_hint: str | None = None) -> str:
    """Grounding Gemini; em 429/falha cai no SearchAPI (fail-soft)."""
    handle = (username or "").strip().lstrip("@")
    nome = (nome_hint or handle).strip()
    try:
        from tools.pipeline_model import DEFAULT_GEMINI_MODEL, gemini_side_tools_ok

        if not gemini_side_tools_ok():
            return ""
        from tools._genai_client import build_genai_client, generate_content_resilient
        from google.genai import types

        prompt = (
            f"Você é um extrator de planos de academia. "
            f"Busque planos e preços públicos da academia '{nome}' "
            f"(Instagram @{handle}, site se houver). "
            f"Responda em markdown curto, listando cada plano no formato:\n"
            f"- Nome do plano: R$ valor\n"
            f"Inclua se é mensal ou anual quando a fonte disser. "
            f"Não invente preço — só o que aparecer na busca. "
            f"Se não achar preço, escreva 'SEM_PRECO'."
        )
        client = build_genai_client()
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.1,
        )
        response = generate_content_resilient(
            client,
            model=DEFAULT_GEMINI_MODEL,
            contents=prompt,
            config=config,
            max_retries=2,
            base_delay=2.0,
        )
        text = getattr(response, "text", None) or ""
        if not text and getattr(response, "candidates", None):
            parts = []
            for c in response.candidates or []:
                content = getattr(c, "content", None)
                for part in getattr(content, "parts", None) or []:
                    t = getattr(part, "text", None)
                    if t:
                        parts.append(t)
            text = "\n".join(parts)
        if text and "R$" in text:
            return text
    except Exception as exc:
        logger.warning(
            "L3.6 Gemini indisponível (@%s): %s — fallback SearchAPI",
            handle,
            type(exc).__name__,
        )

    return _searchapi_markdown_planos(handle, nome_hint=nome)


def enriquecer_oferta_com_highlights_gemini(
    oferta: dict,
    username: str,
    *,
    nome_hint: str | None = None,
    force_refresh: bool = False,
) -> dict:
    """
    L3.6: enriquece oferta com planos sanitizados via Gemini+grounding.
    Mutação defensiva — devolve cópia enriquecida; falha → oferta original.
    """
    if not isinstance(oferta, dict):
        return oferta
    handle = (username or "").strip().lstrip("@").lower()
    if not handle:
        return oferta

    out = dict(oferta)
    out["instagram_username"] = handle

    cached = None if force_refresh else _cache_load(handle)
    if cached and cached.get("status") == "ok":
        markdown = cached.get("markdown") or ""
        planos = cached.get("planos_extraidos") or _extrair_precos_do_markdown(markdown)
        if cached.get("planos_extraidos") is None and planos:
            # Regrava planos sanitizados na próxima leitura
            pass
        out["highlights_gemini"] = {
            "status": "ok",
            "cache_hit": True,
            "markdown_chars": len(markdown),
        }
        out["planos_extraidos"] = planos
        faixa = _faixa_de_planos(planos)
        if faixa:
            out["faixa_preco_brl"] = faixa
        try:
            from tools.competitor_offer_mapper import _detectar_modalidades

            mods = set(out.get("modalidades") or out.get("modalidades_keywords") or [])
            mods |= set(_detectar_modalidades(markdown))
            if "modalidades_keywords" in out and "modalidades" not in out:
                out["modalidades_keywords"] = sorted(mods)
            else:
                out["modalidades"] = sorted(mods)
        except Exception:
            pass
        fontes = list(out.get("fontes") or [])
        if "instagram_highlights_gemini" not in fontes:
            fontes.append("instagram_highlights_gemini")
        out["fontes"] = fontes
        out["instagram_l3_5_status"] = out.get("instagram_l3_5_status") or "ok"
        return out

    try:
        markdown = _gemini_markdown_planos(handle, nome_hint=nome_hint or out.get("nome"))
    except Exception as exc:
        logger.warning(
            "L3.6 Gemini falhou @%s: %s",
            handle,
            type(exc).__name__,
        )
        out["highlights_gemini"] = {
            "status": "erro",
            "erro": type(exc).__name__,
        }
        return out

    if not markdown or "SEM_PRECO" in markdown.upper() and "R$" not in markdown:
        out["highlights_gemini"] = {"status": "sem_preco", "markdown_chars": len(markdown or "")}
        _cache_save(handle, {"status": "sem_preco", "markdown": markdown or ""})
        return out

    planos = _extrair_precos_do_markdown(markdown)
    _cache_save(
        handle,
        {"status": "ok", "markdown": markdown, "planos_extraidos": planos},
    )
    out["highlights_gemini"] = {
        "status": "ok",
        "cache_hit": False,
        "markdown_chars": len(markdown),
        "n_planos": len(planos),
    }
    out["planos_extraidos"] = planos
    faixa = _faixa_de_planos(planos)
    if faixa:
        out["faixa_preco_brl"] = faixa

    # Modalidades extras no texto grounding (dança etc.)
    try:
        from tools.competitor_offer_mapper import _detectar_modalidades

        mods = set(out.get("modalidades") or out.get("modalidades_keywords") or [])
        mods |= set(_detectar_modalidades(markdown))
        if "modalidades" in out or "modalidades_keywords" not in out:
            out["modalidades"] = sorted(mods)
        else:
            out["modalidades_keywords"] = sorted(mods)
    except Exception:
        pass

    fontes = list(out.get("fontes") or [])
    if "instagram_highlights_gemini" not in fontes:
        fontes.append("instagram_highlights_gemini")
    out["fontes"] = fontes
    out["instagram_l3_5_status"] = out.get("instagram_l3_5_status") or "ok"
    return out


def elevar_confianca(atual: str | None, nova: str) -> str:
    hierarquia = {"baixa": 1, "media": 2, "alta": 3}
    atual_val = hierarquia.get((atual or "baixa").lower(), 1)
    nova_val = hierarquia.get((nova or "baixa").lower(), 1)
    max_val = max(atual_val, nova_val)
    for k, v in hierarquia.items():
        if v == max_val:
            return k
    return "baixa"
