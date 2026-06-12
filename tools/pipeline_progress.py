"""Progresso do pipeline por agente — alimenta o stepper do frontend.

Fase 1 do SPEC_PROGRESSO_PIPELINE (12/06): callbacks before/after agent
gravam `relatorios.etapa_atual` e `relatorios.etapas_concluidas` via
Supabase. O front já faz polling de status — passa a ler as etapas e
renderiza stepper + barra ponderada, com copy por FONTE (P-001).

Fail-safe absoluto: qualquer erro aqui é engolido — progresso visual
nunca derruba pipeline.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

# Agentes "folha" que aparecem no stepper (orquestradores ficam de fora).
ETAPAS_VISIVEIS = {
    "ContextBuilder",
    "GeoScout",
    "DemoAnalyst",
    "CompetitorSearch",
    "CompetitorAnalysis",
    "CompetitorMapper",
    "FinancialEstimator",
    "ContactHunter",
    "ReportConsolidator",
    "PositioningStrategist",
}

_inicio_etapa: dict[str, float] = {}


def _sb():
    import os

    from supabase import create_client

    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        return None
    return create_client(url, key)


def _relatorio_id(callback_context: Any) -> str | None:
    try:
        state = getattr(callback_context, "state", None) or {}
        rid = state.get("relatorio_id") if hasattr(state, "get") else None
        return str(rid) if rid else None
    except Exception:
        return None


def _nome_agente(callback_context: Any) -> str | None:
    try:
        return getattr(callback_context, "agent_name", None) or getattr(
            getattr(callback_context, "_invocation_context", None), "agent", None
        )
    except Exception:
        return None


def progress_before_agent(callback_context: Any = None, **kwargs) -> None:
    try:
        nome = _nome_agente(callback_context)
        rid = _relatorio_id(callback_context)
        if not nome or nome not in ETAPAS_VISIVEIS or not rid:
            return
        _inicio_etapa[f"{rid}:{nome}"] = time.time()
        sb = _sb()
        if sb is None:
            return
        sb.table("relatorios").update({"etapa_atual": nome}).eq("id", rid).execute()
    except Exception:
        pass


def progress_after_agent(callback_context: Any = None, **kwargs) -> None:
    try:
        nome = _nome_agente(callback_context)
        rid = _relatorio_id(callback_context)
        if not nome or nome not in ETAPAS_VISIVEIS or not rid:
            return
        t0 = _inicio_etapa.pop(f"{rid}:{nome}", None)
        duracao = round(time.time() - t0, 1) if t0 else None
        sb = _sb()
        if sb is None:
            return
        row = (
            sb.table("relatorios")
            .select("etapas_concluidas")
            .eq("id", rid)
            .maybe_single()
            .execute()
        )
        etapas = list(((row.data or {}).get("etapas_concluidas")) or [])
        if any(e.get("agente") == nome for e in etapas if isinstance(e, dict)):
            return
        etapas.append({
            "agente": nome,
            "fim": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "duracao_s": duracao,
        })
        sb.table("relatorios").update({"etapas_concluidas": etapas}).eq("id", rid).execute()
    except Exception:
        pass
