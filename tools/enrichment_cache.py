"""Cache de enrichment local (scripts/enrichment/cache) para o pipeline ADK."""
from __future__ import annotations

import json
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "scripts" / "enrichment" / "cache"
CACHE_MAX_AGE_DAYS = 7

_pipeline_ctx: ContextVar[dict[str, Any] | None] = ContextVar("pipeline_enrichment_ctx", default=None)

SKIP_TOOL_NAMES = (
    "local_market_facts",
    "aluguel_municipio_portais",
    "bcb_imobiliario_olinda",
)


def _slug(cidade: str, bairro: str, uf: str) -> str:
    parts = [cidade.strip().lower(), (bairro or "").strip().lower(), uf.strip().lower()]
    return "_".join(p for p in parts if p)


def _parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def cache_is_fresh(cache: dict[str, Any], *, max_age_days: int = CACHE_MAX_AGE_DAYS) -> bool:
    ts = _parse_ts(cache.get("gerado_em"))
    if ts is None:
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - ts.astimezone(timezone.utc)
    return age.total_seconds() <= max_age_days * 86400


def load_cache_file(cidade: str, bairro: str, uf: str) -> dict[str, Any] | None:
    path = CACHE_DIR / f"{_slug(cidade, bairro, uf)}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def compress_from_cache(data: dict[str, Any]) -> str:
    from scripts.enrichment.prompt_compressor import compress_from_cache as _compress

    return _compress(data)


def inject_cache_context(
    cidade: str,
    bairro: str,
    uf: str,
    context: dict[str, Any],
    *,
    area_min: int | None = None,
    area_max: int | None = None,
) -> dict[str, Any]:
    """Carrega cache em disco; injeta resumo e skip_tools se fresco (<7 dias)."""
    cache = load_cache_file(cidade, bairro, uf)
    if not cache:
        return context

    context = dict(context)
    context["enrichment_cache"] = cache
    context["cache_key"] = cache.get("cache_key")
    context["local_market_summary"] = compress_from_cache(cache)

    if cache_is_fresh(cache):
        context["skip_tools"] = list(SKIP_TOOL_NAMES)
        context["enrichment_cache_fresh"] = True
    else:
        context["enrichment_cache_fresh"] = False

    if area_min is not None:
        context.setdefault("enrichment_area_min", area_min)
    if area_max is not None:
        context.setdefault("enrichment_area_max", area_max)
    return context


def set_pipeline_enrichment_context(ctx: dict[str, Any] | None) -> Any:
    """Define contexto do pipeline; retorna token para reset()."""
    return _pipeline_ctx.set(ctx)


def reset_pipeline_enrichment_context(token: Any) -> None:
    _pipeline_ctx.reset(token)


def get_pipeline_enrichment_context() -> dict[str, Any] | None:
    return _pipeline_ctx.get()


def should_skip_tool(tool_name: str) -> bool:
    ctx = get_pipeline_enrichment_context()
    if not ctx or not ctx.get("enrichment_cache_fresh"):
        return False
    skip = ctx.get("skip_tools") or []
    return tool_name in skip


def cached_competicao_local() -> dict[str, Any] | None:
    if not should_skip_tool("local_market_facts"):
        return None
    cache = (get_pipeline_enrichment_context() or {}).get("enrichment_cache") or {}
    comp = cache.get("competicao_local")
    if isinstance(comp, dict) and comp.get("status") == "ok":
        return dict(comp)
    return None


def cached_aluguel_portais() -> dict[str, Any] | None:
    if not should_skip_tool("aluguel_municipio_portais"):
        return None
    cache = (get_pipeline_enrichment_context() or {}).get("enrichment_cache") or {}
    al = cache.get("aluguel_portais")
    if isinstance(al, dict) and al.get("n_validos") is not None:
        return dict(al)
    return None


def cached_bcb_imobiliario() -> dict[str, Any] | None:
    if not should_skip_tool("bcb_imobiliario_olinda"):
        return None
    cache = (get_pipeline_enrichment_context() or {}).get("enrichment_cache") or {}
    bcb = cache.get("bcb_imobiliario")
    if isinstance(bcb, dict) and bcb:
        return dict(bcb)
    return None
