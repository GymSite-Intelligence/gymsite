"""SearchAPI Account + Analytics → rota de custo / budget guard.

O tracking per-run (api_cost_tracker) ESTIMA o custo SearchAPI por relatório.
Aqui pegamos o REAL agregado da conta (Account API, free) p/ reconciliar e
guardar orçamento. Analytics API é gated (Scale+) → best-effort.

Account API:   GET /api/v1/me              (free, qualquer plano)
Analytics API: GET /api/v1/search_analytics (requer Scale+)
"""
from __future__ import annotations

import os
from typing import Any

_BASE = "https://www.searchapi.io/api/v1"

# Custo por search (USD). Plano padrão $40 / 10k searches = $0.004. Override por env.
SEARCHAPI_USD_PER_SEARCH = float(os.getenv("SEARCHAPI_USD_PER_SEARCH") or "0.004")

# Limiares do budget guard (% da allowance mensal consumida).
_PCT_ALERTA = float(os.getenv("SEARCHAPI_BUDGET_ALERTA_PCT") or "80")
_PCT_CRITICO = float(os.getenv("SEARCHAPI_BUDGET_CRITICO_PCT") or "95")


def _key() -> str:
    return (os.getenv("SEARCHAPI_KEY") or "").strip()


def get_account() -> dict[str, Any]:
    """Estado da conta via Account API (free). Best-effort: erro → {_ok: False}."""
    import requests

    key = _key()
    if not key:
        return {"_ok": False, "_erro": "SEARCHAPI_KEY ausente"}
    try:
        r = requests.get(
            f"{_BASE}/me", headers={"Authorization": f"Bearer {key}"}, timeout=20
        )
        r.raise_for_status()
        b = r.json()
    except Exception as e:
        return {"_ok": False, "_erro": f"{type(e).__name__}"}

    acc = b.get("account") or {}
    sub = b.get("subscription") or {}
    return {
        "_ok": True,
        "usage_mes": int(acc.get("current_month_usage") or 0),
        "allowance_mes": int(acc.get("monthly_allowance") or 0),
        "remaining_credits": int(acc.get("remaining_credits") or 0),
        "period_start": sub.get("period_start"),
        "period_end": sub.get("period_end"),
    }


def resumo_orcamento() -> dict[str, Any]:
    """Budget guard p/ a rota de custo: usado, restante real, % e status.

    Restante REAL = allowance - usage (o free tier que de fato é consumido).
    `remaining_credits` (créditos pagos extra) é exposto à parte — pode ser 0
    sem bloquear o free tier.
    """
    acc = get_account()
    if not acc.get("_ok"):
        return {"_ok": False, "_erro": acc.get("_erro"), "status": "desconhecido"}

    usado = acc["usage_mes"]
    allowance = acc["allowance_mes"]
    restante = max(0, allowance - usado)
    pct = round(100 * usado / allowance, 1) if allowance else 0.0

    if pct >= _PCT_CRITICO:
        status = "critico"
    elif pct >= _PCT_ALERTA:
        status = "alerta"
    else:
        status = "ok"

    return {
        "_ok": True,
        "usado": usado,
        "allowance": allowance,
        "restante": restante,
        "remaining_credits_pagos": acc["remaining_credits"],
        "pct_consumido": pct,
        "status": status,
        "custo_mes_usd": round(usado * SEARCHAPI_USD_PER_SEARCH, 4),
        "custo_restante_usd": round(restante * SEARCHAPI_USD_PER_SEARCH, 4),
        "period_start": acc["period_start"],
        "period_end": acc["period_end"],
    }


def get_analytics(time_period: str = "last_month", engine: str | None = None) -> dict[str, Any]:
    """Analytics agregada (gated: Scale+). Degrada p/ {_disponivel: False} em 403."""
    import requests

    key = _key()
    if not key:
        return {"_disponivel": False, "_motivo": "SEARCHAPI_KEY ausente"}
    params: dict[str, Any] = {"time_period": time_period}
    if engine:
        params["engine"] = engine
    try:
        r = requests.get(
            f"{_BASE}/search_analytics",
            headers={"Authorization": f"Bearer {key}"},
            params=params,
            timeout=20,
        )
        if r.status_code == 403:
            return {"_disponivel": False, "_motivo": "requer plano Scale+"}
        r.raise_for_status()
        b = r.json()
    except Exception as e:
        return {"_disponivel": False, "_motivo": f"{type(e).__name__}"}

    resumo = b.get("summary") or {}
    return {
        "_disponivel": True,
        "total_searches": int(resumo.get("total_searches") or 0),
        "success_rate": resumo.get("success_rate"),
        "avg_speed_time_s": resumo.get("avg_speed_time_s"),
        "por_engine": b.get("performance_by_engine") or [],
        "buckets": b.get("buckets") or [],
    }
