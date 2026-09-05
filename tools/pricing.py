"""
tools/pricing.py — preços oficiais Gemini em BRL (extraídos do CSV de billing
do Google Cloud: "Preço para My Billing Account 1 (1).csv").

Unidade: R$ por **1 milhão** de tokens.
Fonte: Vertex AI / Gemini API — preços de tabela em BRL.

Funções:
    compute_cost_brl(model, tokens_in, tokens_out) -> float
    aggregate_run_costs(rows) -> { tokens_in, tokens_out, custo_brl, por_agente }
"""
from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Preços por 1M tokens em BRL — extraídos do CSV de billing Google Cloud
# (consultado 2026-05-29). Vertex AI e Gemini API têm preços idênticos.
# ---------------------------------------------------------------------------
PRICING_BRL_PER_MILLION: dict[str, dict[str, float]] = {
    # Gemini 2.5 Flash GA — Text Input / Output (standard, não batch/priority)
    "gemini-2.5-flash": {
        "input": 1.703181374,
        "output": 14.193178124,
    },
    # Gemini 2.5 Flash Lite — mais barato, usado em A3b competitor_analysis
    "gemini-2.5-flash-lite": {
        "input": 0.567727124,
        "output": 2.270908499,
    },
    # Gemini 2.5 Pro — usado em A4 (financial_estimator) e A6 (report_consolidator)
    "gemini-2.5-pro": {
        "input": 7.096589062,    # short context (<=128k)
        "output": 56.772712499,  # short context
    },
    # Fallbacks compatíveis
    "gemini-2.0-flash": {
        "input": 0.851590687,
        "output": 3.406362749,
    },
    "gemini-2.0-flash-lite": {
        "input": 0.425795343,
        "output": 1.703181374,
    },
}

# Google Maps Platform — preços por 1.000 chamadas (BRL, do mesmo CSV)
MAPS_API_BRL_PER_1K: dict[str, float] = {
    # Places API (New) — Nearby Search / Text Search
    "places_search_new": 181.672679999,
    # Places API (New) — Details
    "places_details_new": 96.513611249,
    # Places API (New) — Autocomplete per request
    "places_autocomplete": 16.066677637,
    # Geocoding API
    "geocoding": 28.386356249,
    # Distance Matrix API
    "distance_matrix": 28.386356249,
    # Directions API
    "directions": 28.386356249,
}

# Preço em BRL por chamada individual (divide por 1000)
MAPS_API_BRL_PER_CALL: dict[str, float] = {
    k: v / 1000.0 for k, v in MAPS_API_BRL_PER_1K.items()
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _lookup_model(model_raw: str | None) -> str | None:
    """Normaliza p/ a chave de preço. Robusto a 'models/gemini-2.5-flash' E ao repr
    do objeto Gemini do ADK (\"model='gemini-2.5-flash' ... retry_options=...\") — o
    wrap de retry passou a logar o repr inteiro no telemetry; sem isto o custo LLM zera.
    """
    if not model_raw:
        return None
    m = model_raw.strip().lower()
    if m.startswith("models/"):
        m = m[len("models/"):]
    # match direto (nome limpo)
    for known in PRICING_BRL_PER_MILLION:
        if m == known or m.startswith(known + "-"):
            return known
    # fallback: extrai 'gemini-X.Y-variante' de qualquer string (repr do Gemini, etc.)
    import re as _re
    mm = _re.search(r"gemini-[0-9.]+-[a-z-]+", m)
    if mm:
        cand = mm.group(0)
        # 1) match EXATO primeiro (senão 'flash-lite' casaria 'flash' por prefixo)
        if cand in PRICING_BRL_PER_MILLION:
            return cand
        # 2) prefixo, preferindo a chave conhecida MAIS LONGA que casa
        candidatos = [k for k in PRICING_BRL_PER_MILLION if cand.startswith(k + "-")]
        if candidatos:
            return max(candidatos, key=len)
    return None


def compute_cost_brl(model: str | None, tokens_in: int, tokens_out: int) -> float:
    """Custo em BRL para um par (model, in, out). Modelo desconhecido → 0.0."""
    key = _lookup_model(model)
    if not key:
        return 0.0
    p = PRICING_BRL_PER_MILLION[key]
    return ((tokens_in or 0) * p["input"] + (tokens_out or 0) * p["output"]) / 1_000_000.0


def compute_maps_cost_brl(api: str, num_calls: int) -> float:
    """Custo BRL pra N chamadas de uma SKU da Maps API."""
    per_call = MAPS_API_BRL_PER_CALL.get(api, 0.0)
    return per_call * max(0, num_calls)


def aggregate_run_costs(rows: list[dict]) -> dict:
    """
    Agrega linhas do tokens_pipeline.csv num sumário por run.
    Espera keys: model, tokens_in, tokens_out, agent_name.

    Retorna:
        {
            tokens_in_total: int,
            tokens_out_total: int,
            tokens_total: int,
            custo_brl_total: float,
            por_agente: { agent_name: {tokens_in, tokens_out, custo_brl, model} },
        }
    """
    tot_in = tot_out = 0
    custo_total = 0.0
    por_agente: dict[str, dict] = {}

    for r in rows:
        ti = int(r.get("tokens_in") or 0)
        to = int(r.get("tokens_out") or 0)
        model = r.get("model") or ""
        custo = compute_cost_brl(model, ti, to)

        tot_in += ti
        tot_out += to
        custo_total += custo

        agente = r.get("agent_name") or "?"
        slot = por_agente.setdefault(
            agente,
            {"tokens_in": 0, "tokens_out": 0, "custo_brl": 0.0, "model": model},
        )
        slot["tokens_in"] += ti
        slot["tokens_out"] += to
        slot["custo_brl"] = round(slot["custo_brl"] + custo, 6)
        if model:
            slot["model"] = model

    return {
        "tokens_in_total": tot_in,
        "tokens_out_total": tot_out,
        "tokens_total": tot_in + tot_out,
        "custo_brl_total": round(custo_total, 6),
        "por_agente": por_agente,
    }


# ---------------------------------------------------------------------------
# Compatibilidade legada (USD) — mantida para não quebrar código antigo
# ---------------------------------------------------------------------------
USD_BRL_RATE_DEFAULT = 5.40


def usd_brl_rate() -> float:
    """Taxa USD→BRL (legado)."""
    raw = os.environ.get("USD_BRL_RATE", "").strip()
    try:
        if raw:
            return float(raw)
    except ValueError:
        pass
    return USD_BRL_RATE_DEFAULT


# Preços legados em USD (aproximados) — usados só se alguém chamar compute_cost_usd
_PRICING_USD_PER_MILLION: dict[str, dict[str, float]] = {
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
    "gemini-2.0-flash": {"input": 0.15, "output": 0.60},
}


def compute_cost_usd(model: str | None, tokens_in: int, tokens_out: int) -> float:
    """USD legado (aproximado). Novo código deve usar compute_cost_brl."""
    key = _lookup_model(model)
    if not key:
        return 0.0
    p = _PRICING_USD_PER_MILLION.get(key, {"input": 0.0, "output": 0.0})
    return ((tokens_in or 0) * p["input"] + (tokens_out or 0) * p["output"]) / 1_000_000.0


# SearchAPI: cada search = 1 crédito. Plano padrão $40 / 10k = $0.004/search.
# Antes era 0.0 → custo SearchAPI ficava INVISÍVEL na rota de custo. Override por env.
_SEARCHAPI_USD = float(os.getenv("SEARCHAPI_USD_PER_SEARCH") or "0.004")

# Compatibilidade legada Places API em USD
PLACES_API_USD_PER_CALL: dict[str, float] = {
    "places_details_legacy": 0.017,
    "places_search_new": 0.032,
    "places_details_new": 0.020,
    "places_aggregate": 0.040,  # areaInsights INSIGHT_COUNT (com filtros rating/tipo) — tier caro
    "geocoding": 0.005,
    "searchapi_popular_times": _SEARCHAPI_USD,
    "searchapi_google_maps_place": _SEARCHAPI_USD,
    "searchapi_google_light": _SEARCHAPI_USD,
    "site_oficial_html": 0.0,  # scrape balcão — sem SearchAPI
    "wikipedia_mediawiki": 0.0,
    "wikipedia_wikidata": 0.0,
    "searchapi_google_maps": _SEARCHAPI_USD,
    "searchapi_instagram_profile": _SEARCHAPI_USD,
    "searchapi_google_maps_reviews": _SEARCHAPI_USD,
    "searchapi_locations": 0.0,  # Locations API é free
    "outscraper_popular_times": 0.003,
}


def compute_places_cost_usd(api: str, num_calls: int) -> float:
    per_call = PLACES_API_USD_PER_CALL.get(api, 0.0)
    return per_call * max(0, num_calls)


def compute_places_cost_brl(api: str, num_calls: int) -> float:
    return round(compute_places_cost_usd(api, num_calls) * usd_brl_rate(), 4)
