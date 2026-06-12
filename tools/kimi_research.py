"""
Kimi / OpenClaw market research para o A0 (substitui ou complementa Deep Research Gemini).

Env:
  A0_RESEARCH_PROVIDER=kimi|openclaw|gemini  — kimi usa este módulo no rodar_deep_research
  OPENCLAW_URL                             — base do serviço (ex: https://openclaw.example.com)
  OPENCLAW_TOKEN                           — Bearer opcional
  OPENCLAW_KIMI_SEARCH_PATH                — default /v1/kimi/search
  KIMI_RESEARCH_TIMEOUT_SEC                — default 90 por query
  KIMI_RESEARCH_PARALLEL                   — default 5 queries
  KIMI_RESEARCH_FALLBACK                   — gemini|briefing (se OpenClaw falhar)

Resposta OpenClaw esperada (JSON): { "result": "..." } ou { "text": "..." }
"""
from __future__ import annotations

import asyncio
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime
from typing import Any
import httpx

from tools.deep_research_tool import (
    _briefing_padrao,
    _cache_path,
    _cache_valido,
    _gravar_cache,
    _parse_cache_tier,
)

_last_kimi_tier: str | None = None

_URL_RE = re.compile(r"https?://[^\s\)\]\"'<>]+", re.I)


def get_last_kimi_tier() -> str | None:
    return _last_kimi_tier


def kimi_provider_ativo() -> bool:
    try:
        from tools.research_provider import get_a0_research_provider

        return get_a0_research_provider() == "kimi"
    except Exception:
        p = (os.getenv("A0_RESEARCH_PROVIDER") or "").strip().lower()
        return p in ("kimi", "openclaw", "kimi_research")


def _openclaw_configured() -> bool:
    return bool((os.getenv("OPENCLAW_URL") or "").strip())


def _timeout_per_query() -> float:
    return float(os.getenv("KIMI_RESEARCH_TIMEOUT_SEC", "90"))


def _extrair_urls(texto: str) -> list[str]:
    urls = []
    for m in _URL_RE.findall(texto or ""):
        u = m.rstrip(".,;)")
        if u not in urls:
            urls.append(u)
    return urls[:30]


def _queries_paralelas(
    cidade: str,
    bairro: str,
    tipo_negocio: str,
    publico_alvo: str,
) -> list[tuple[str, str]]:
    """(slug, query) para pesquisas paralelas."""
    return [
        (
            "demografia",
            f"demografia bairro {bairro} {cidade} Brasil população renda IBGE Censo 2022",
        ),
        (
            "tendencias_fitness",
            f"mercado fitness {tipo_negocio} bairro {bairro} {cidade} tendências 2025 2026",
        ),
        (
            "benchmarks",
            f"benchmark academia Brasil ticket médio LTV retenção payback {publico_alvo}",
        ),
        (
            "concorrencia",
            f"concorrência academias bairro {bairro} {cidade} saturação redes",
        ),
        (
            "economia_local",
            f"economia local bairro {bairro} {cidade} comércio poder aquisitivo",
        ),
    ]


async def kimi_search(query: str) -> str:
    """
    Uma pesquisa via OpenClaw HTTP. Levanta RuntimeError se não configurado ou HTTP erro.
    """
    base = (os.getenv("OPENCLAW_URL") or "").strip().rstrip("/")
    if not base:
        raise RuntimeError("OPENCLAW_URL não configurado")

    path = (os.getenv("OPENCLAW_KIMI_SEARCH_PATH") or "/v1/kimi/search").strip()
    if not path.startswith("/"):
        path = "/" + path
    url = f"{base}{path}"

    headers: dict[str, str] = {"Content-Type": "application/json"}
    token = (os.getenv("OPENCLAW_TOKEN") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {
        "query": query,
        "source": "gymsite_a0",
    }

    timeout = _timeout_per_query()
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            body = resp.text[:400]
            raise RuntimeError(f"OpenClaw HTTP {resp.status_code}: {body}")

        if resp.headers.get("content-type", "").startswith("application/json"):
            data = resp.json()
            if isinstance(data, dict):
                for key in ("result", "text", "content", "markdown", "output"):
                    val = data.get(key)
                    if isinstance(val, str) and val.strip():
                        return val.strip()
                if isinstance(data.get("data"), dict):
                    inner = data["data"]
                    for key in ("result", "text"):
                        if isinstance(inner.get(key), str) and inner[key].strip():
                            return inner[key].strip()
            raise RuntimeError("OpenClaw respondeu JSON sem campo result/text")

        text = resp.text.strip()
        if text:
            return text
        raise RuntimeError("OpenClaw respondeu vazio")


def _kimi_search_sync(query: str) -> str:
    return asyncio.run(kimi_search(query))


def _grounded_single_query(query: str) -> str:
    """Fallback: uma query via Gemini grounded (mesmo tier do deep_research_tool)."""
    from tools.deep_research_tool import _executar_grounded_fallback

    deadline = time.time() + min(_timeout_per_query(), 120)
    return _executar_grounded_fallback(
        f"Responda em português (Brasil), markdown, com fontes URL quando possível:\n\n{query}",
        deadline=deadline,
    )


async def _run_parallel_research(
    cidade: str,
    bairro: str,
    tipo_negocio: str,
    publico_alvo: str,
) -> tuple[str, str, list[str]]:
    """
    Executa N pesquisas paralelas. Retorna (markdown, tier, fontes_urls).
    """
    global _last_kimi_tier

    queries = _queries_paralelas(cidade, bairro, tipo_negocio, publico_alvo)
    use_openclaw = _openclaw_configured()
    fallback = (os.getenv("KIMI_RESEARCH_FALLBACK") or "gemini").strip().lower()

    async def _one(slug: str, q: str) -> tuple[str, str, str]:
        if use_openclaw:
            try:
                txt = await kimi_search(q)
                return slug, txt, "openclaw"
            except Exception as exc:
                if fallback == "briefing":
                    return slug, f"*Pesquisa indisponível ({exc})*", "openclaw_erro"
                txt = await asyncio.to_thread(_grounded_single_query, q)
                return slug, txt, "openclaw+gemini_fallback"
        if fallback == "gemini":
            txt = await asyncio.to_thread(_grounded_single_query, q)
            return slug, txt, "gemini_grounded"
        return slug, f"*Configure OPENCLAW_URL ou KIMI_RESEARCH_FALLBACK=gemini*", "indisponivel"

    results = await asyncio.gather(*[_one(s, q) for s, q in queries])

    secoes: list[str] = []
    fontes: list[str] = []
    tiers: set[str] = set()

    titulos = {
        "demografia": "Perfil demográfico",
        "tendencias_fitness": "Mercado fitness local",
        "benchmarks": "Benchmarks setoriais",
        "concorrencia": "Concorrência qualitativa",
        "economia_local": "Economia local",
    }

    for slug, texto, tier in results:
        tiers.add(tier)
        fontes.extend(_extrair_urls(texto))
        secoes.append(f"## {titulos.get(slug, slug)}\n\n{texto.strip()}\n")

    hoje = datetime.now().strftime("%Y-%m-%d")
    header = (
        f"# Briefing de Mercado (Kimi Research) — {bairro}, {cidade}\n\n"
        f"**Data:** {hoje}\n"
        f"**Tipo:** {tipo_negocio} · **Público:** {publico_alvo}\n\n"
    )
    md = header + "\n".join(secoes)

    if use_openclaw and "openclaw_erro" not in tiers:
        tier_label = "kimi:openclaw"
    elif "gemini_grounded" in tiers or "openclaw+gemini_fallback" in tiers:
        tier_label = "kimi:gemini_grounded"
    else:
        tier_label = "kimi:indisponivel"

    _last_kimi_tier = tier_label
    return md, tier_label, list(dict.fromkeys(fontes))


def _consolidar_markdown(
    cidade: str,
    bairro: str,
    corpo: str,
    tier: str,
    fontes: list[str],
) -> str:
    fontes_block = ""
    if fontes:
        fontes_block = "\n\n## Fontes verificadas\n\n" + "\n".join(f"- {u}" for u in fontes)
    return corpo + fontes_block


def rodar_kimi_research(
    cidade: str,
    bairro: str,
    *,
    tipo_negocio: str = "academia",
    publico_alvo: str = "premium",
    force_refresh: bool = False,
) -> str:
    """
    Pesquisa de mercado estilo Kimi (OpenClaw paralelo ou Gemini grounded).
    Grava no mesmo cache markdown que rodar_deep_research. Nunca lança para o ADK.
    """
    global _last_kimi_tier

    # Guardrail duro — mesmo bloqueio do rodar_deep_research (modo estrito).
    from tools.market_bundle import must_not_call_deep_research

    if must_not_call_deep_research():
        _last_kimi_tier = "bloqueado_modo_estrito"
        return (
            f"<!-- kimi_research status=bloqueado cidade={cidade} bairro={bairro} -->\n\n"
            "Pesquisa Kimi desativada (A0_CONTEXT_SOURCE=ckan_bundle). "
            "Use exclusivamente o market_bundle e as tools CNPJ/CNO; campos sem "
            "dado ficam como dados_nao_disponiveis."
        )

    cache = _cache_path(cidade, bairro)
    if not force_refresh and _cache_valido(cache):
        tier_cached = _parse_cache_tier(cache.read_text(encoding="utf-8")[:500])
        if tier_cached and tier_cached.startswith("kimi:"):
            _last_kimi_tier = tier_cached
            return cache.read_text(encoding="utf-8")

    timeout_total = int(os.getenv("KIMI_RESEARCH_TIMEOUT_SEC", "90")) * 6 + 60

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(
                asyncio.run,
                _run_parallel_research(cidade, bairro, tipo_negocio, publico_alvo),
            )
            corpo, tier, fontes = fut.result(timeout=timeout_total)
    except (FuturesTimeout, Exception):
        _last_kimi_tier = "kimi:briefing_padrao"
        return _briefing_padrao(cidade, bairro)

    md = _consolidar_markdown(cidade, bairro, corpo, tier, fontes)
    try:
        _gravar_cache(cidade, bairro, tier, md)
        return _cache_path(cidade, bairro).read_text(encoding="utf-8")
    except Exception:
        header = (
            f"<!-- Deep Research cache\n"
            f"     cidade: {cidade}\n"
            f"     bairro: {bairro}\n"
            f"     tier: {tier}\n"
            f"     data: {datetime.now().isoformat()}\n"
            f"-->\n\n"
        )
        return header + md


def executar_kimi_research_kimi(
    cidade: str,
    bairro: str,
    tipo_negocio: str = "academia",
    publico_alvo: str = "premium",
) -> dict[str, Any]:
    """
    Interface compatível com briefing do integration guide (para API/tools).
    """
    md = rodar_kimi_research(
        cidade,
        bairro,
        tipo_negocio=tipo_negocio,
        publico_alvo=publico_alvo,
        force_refresh=True,
    )
    tier = get_last_kimi_tier() or "kimi:unknown"
    fontes = _extrair_urls(md)
    return {
        "status": "ok",
        "tier": tier,
        "insights_deep_research": md,
        "fontes_verificadas": fontes,
        "confidence_score": min(1.0, len(fontes) / 5.0) if fontes else 0.4,
        "openclaw_configured": _openclaw_configured(),
    }
