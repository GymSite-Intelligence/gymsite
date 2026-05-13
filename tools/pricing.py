"""
tools/pricing.py — preços oficiais Gemini + conversão pra BRL.

Fonte: https://ai.google.dev/gemini-api/docs/pricing (consultado 2026-05-12)

Preços são por **1 milhão** de tokens, separados por input (prompt) e output
(candidate). Search Grounding e Caching têm preço próprio; aqui ficamos
no básico de input/output que cobre >95% do custo do pipeline.

Câmbio USD→BRL é configurável via env `USD_BRL_RATE` (default 5.40 — ajustar
mensalmente conforme cotação atual). Em produção, plugar API de câmbio
(Banco Central) é trivial.

Funções:
    compute_cost_usd(model, tokens_in, tokens_out) -> float
    compute_cost_brl(model, tokens_in, tokens_out) -> float
    aggregate_run_costs(rows) -> { tokens_in, tokens_out, custo_brl }
"""
from __future__ import annotations

import os

USD_BRL_RATE_DEFAULT = 5.40


def usd_brl_rate() -> float:
    """Taxa atual USD→BRL. Override via env `USD_BRL_RATE`."""
    raw = os.environ.get("USD_BRL_RATE", "").strip()
    try:
        if raw:
            return float(raw)
    except ValueError:
        pass
    return USD_BRL_RATE_DEFAULT


# Preço por 1M tokens em USD. Vertex AI tem o MESMO preço da Gemini API
# direta (única diferença é auth/quota), então essa tabela serve pros dois.
#
# Inclui ambos os esquemas de naming: "models/gemini-2.5-flash" (ADK) e
# "gemini-2.5-flash" (raw API). lookup_model normaliza.
PRICING_USD_PER_MILLION: dict[str, dict[str, float]] = {
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "gemini-2.5-pro":   {"input": 1.25, "output": 10.00},
    "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
}

# Google Maps Platform — preços por chamada (não por 1M).
# Fonte: https://mapsplatform.google.com/pricing/ (consultado 2026-05-12)
PLACES_API_USD_PER_CALL: dict[str, float] = {
    # Places API Legacy — usado por populartimes lib (Tier 1 popular_times).
    "places_details_legacy": 0.017,
    # Places API New — Nearby Search / Text Search (A1 GeoScout, A3a).
    "places_search_new": 0.032,
    # Places API New — Details (contact data, reviews).
    "places_details_new": 0.020,
    # Geocoding API.
    "geocoding": 0.005,
    # Tier 0 popular_times: SearchAPI (free 100 req/mês, depois $25/5000).
    "searchapi_popular_times": 0.0,
    # Tier 0 alternativa: Outscraper pay-per-use (~$0,003/place).
    "outscraper_popular_times": 0.003,
}


def compute_places_cost_usd(api: str, num_calls: int) -> float:
    """Custo USD pra N chamadas de uma SKU da Places API."""
    per_call = PLACES_API_USD_PER_CALL.get(api, 0.0)
    return per_call * max(0, num_calls)


def compute_places_cost_brl(api: str, num_calls: int) -> float:
    """Custo BRL com câmbio atual. Arredonda em 4 casas."""
    return round(compute_places_cost_usd(api, num_calls) * usd_brl_rate(), 4)


def _lookup_model(model_raw: str | None) -> str | None:
    """Normaliza nomes do tipo 'models/gemini-2.5-flash' → 'gemini-2.5-flash'."""
    if not model_raw:
        return None
    m = model_raw.strip().lower()
    if m.startswith("models/"):
        m = m[len("models/"):]
    # alguns retornam com sufixo de versão (e.g. -001, -002)
    for known in PRICING_USD_PER_MILLION:
        if m == known or m.startswith(known + "-"):
            return known
    return None


def compute_cost_usd(model: str | None, tokens_in: int, tokens_out: int) -> float:
    """USD pra um par (model, in, out). Modelo desconhecido → 0.0."""
    key = _lookup_model(model)
    if not key:
        return 0.0
    p = PRICING_USD_PER_MILLION[key]
    return ((tokens_in or 0) * p["input"] + (tokens_out or 0) * p["output"]) / 1_000_000.0


def compute_cost_brl(model: str | None, tokens_in: int, tokens_out: int) -> float:
    """BRL com câmbio atual. Arredonda em 4 casas (centavos têm precisão >2)."""
    return round(compute_cost_usd(model, tokens_in, tokens_out) * usd_brl_rate(), 4)


def aggregate_run_costs(rows: list[dict]) -> dict:
    """
    Agrega linhas do tokens_pipeline.csv (ou estrutura equivalente) num
    sumário por run. Espera keys: model, tokens_in, tokens_out.

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
        slot["custo_brl"] = round(slot["custo_brl"] + custo, 4)
        # Mantém último modelo visto pro agente (em geral só usa 1)
        if model:
            slot["model"] = model

    return {
        "tokens_in_total": tot_in,
        "tokens_out_total": tot_out,
        "tokens_total": tot_in + tot_out,
        "custo_brl_total": round(custo_total, 4),
        "por_agente": por_agente,
    }
