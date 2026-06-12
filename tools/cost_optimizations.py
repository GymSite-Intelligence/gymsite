"""
tools/cost_optimizations.py — Análise de oportunidades de economia no pipeline.

Lê metrics/tokens_pipeline.csv, cruza com tabela de preços BRL (do CSV de billing)
e gera sugestões acionáveis com economia estimada.

Tipos de otimização detectados:
    1. MODELO_OVERPRICED   → agente usando Pro onde Flash/Lite seria suficiente
    2. AGENTE_VORAZ        → agente consumindo >50% do custo total
    3. ERRO_REPETIDO       → alta taxa de finish_reason != STOP
    4. CACHE_GEOCODING     → chamadas repetidas de geocoding pra mesma cidade
    5. FLASH_PARA_LITE     → agente usando Flash onde Lite seria suficiente
"""
from __future__ import annotations

import csv
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tools.pricing import PRICING_BRL_PER_MILLION, compute_cost_brl

PIPELINE_CSV = Path("metrics/tokens_pipeline.csv")
DEFAULT_DIAS = 30

# Mapeamento de agentes → modelo "ideal" mais barato que não perde qualidade
# Baseado no conhecimento do domínio de cada agente
AGENTE_MODELO_SUGERIDO: dict[str, str] = {
    "a0_context_builder": "gemini-2.5-flash",
    "a1_geoscout": "gemini-2.5-flash",
    "a2_demo_analyst": "gemini-2.5-flash",
    "a3_competitor_intel": "gemini-2.5-flash",
    "a3a_competitor_search": "gemini-2.5-flash",
    "a3b_competitor_analysis": "gemini-2.5-flash-lite",  # já usa lite
    "a3c_competitor_mapper": "gemini-2.5-flash",
    "a4_financial_estimator": "gemini-2.5-flash",  # aritmética estruturada; Pro→Flash 12/06 (golden case pendente)
    "a5_contact_hunter": "gemini-2.5-flash",
    "a6_report_consolidator": "gemini-2.5-pro",  # síntese final, justifica Pro
    "a7_market_research": "gemini-2.5-flash",
}


def _parse_dt_iso(val: str) -> datetime | None:
    try:
        # suporta "2026-05-29T12:34:56" e "2026-05-29T12:34:56.123456+00:00"
        val = val.strip()
        if val.endswith("Z"):
            val = val[:-1] + "+00:00"
        return datetime.fromisoformat(val)
    except Exception:
        return None


def _ler_pipeline(dias: int = DEFAULT_DIAS) -> list[dict]:
    """Lê linhas do CSV dos últimos N dias."""
    if not PIPELINE_CSV.exists():
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=dias)
    rows: list[dict] = []

    with PIPELINE_CSV.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            dt = _parse_dt_iso(r.get("timestamp", ""))
            if dt is None:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt >= cutoff:
                rows.append(r)
    return rows


def _agregar_por_agente(rows: list[dict]) -> dict[str, dict]:
    """Agrega métricas por agente."""
    agg: dict[str, dict] = defaultdict(
        lambda: {
            "tokens_in": 0,
            "tokens_out": 0,
            "calls": 0,
            "model": "",
            "finish_reasons": Counter(),
            "custo_brl": 0.0,
            "custo_brl_com_flash": 0.0,
            "custo_brl_com_lite": 0.0,
        }
    )

    for r in rows:
        agente = r.get("agent_name") or "?"
        ti = int(r.get("tokens_in") or 0)
        to = int(r.get("tokens_out") or 0)
        model = r.get("model") or ""
        finish = r.get("finish_reason") or "STOP"

        a = agg[agente]
        a["tokens_in"] += ti
        a["tokens_out"] += to
        a["calls"] += 1
        a["finish_reasons"][finish] += 1
        if model:
            a["model"] = model

        # custo real
        a["custo_brl"] += compute_cost_brl(model, ti, to)
        # custo hipotético se usasse flash
        a["custo_brl_com_flash"] += compute_cost_brl("gemini-2.5-flash", ti, to)
        # custo hipotético se usasse lite
        a["custo_brl_com_lite"] += compute_cost_brl("gemini-2.5-flash-lite", ti, to)

    return dict(agg)


def _detectar_modelo_overpriced(agg: dict[str, dict]) -> list[dict]:
    """Agentes usando Pro onde Flash/Lite seria suficiente."""
    sugestoes: list[dict] = []
    for agente, dados in agg.items():
        model_atual = dados["model"]
        if not model_atual:
            continue
        model_sugerido = AGENTE_MODELO_SUGERIDO.get(agente)
        if not model_sugerido:
            continue
        if model_atual == model_sugerido:
            continue

        # Se está usando Pro mas deveria usar Flash
        if "pro" in model_atual and "flash" in model_sugerido:
            economia = dados["custo_brl"] - dados["custo_brl_com_flash"]
            if economia > 0.01:
                sugestoes.append({
                    "tipo": "MODELO_OVERPRICED",
                    "agente": agente,
                    "modelo_atual": model_atual,
                    "modelo_sugerido": model_sugerido,
                    "economia_brl": round(economia, 4),
                    "detalhe": (
                        f"{agente} usa {model_atual} (R$ {dados['custo_brl']:.4f}). "
                        f"Trocar por {model_sugerido} economizaria R$ {economia:.4f} "
                        f"({economia / max(dados['custo_brl'], 0.001) * 100:.1f}%)."
                    ),
                    "severidade": "alta" if economia > 1.0 else "media",
                })

        # Se está usando Flash mas deveria usar Lite
        if model_atual == "gemini-2.5-flash" and model_sugerido == "gemini-2.5-flash-lite":
            economia = dados["custo_brl"] - dados["custo_brl_com_lite"]
            if economia > 0.01:
                sugestoes.append({
                    "tipo": "FLASH_PARA_LITE",
                    "agente": agente,
                    "modelo_atual": model_atual,
                    "modelo_sugerido": model_sugerido,
                    "economia_brl": round(economia, 4),
                    "detalhe": (
                        f"{agente} usa {model_atual} (R$ {dados['custo_brl']:.4f}). "
                        f"Trocar por {model_sugerido} economizaria R$ {economia:.4f} "
                        f"({economia / max(dados['custo_brl'], 0.001) * 100:.1f}%)."
                    ),
                    "severidade": "baixa" if economia < 0.5 else "media",
                })

    return sorted(sugestoes, key=lambda x: x["economia_brl"], reverse=True)


def _detectar_agente_voraz(agg: dict[str, dict], total_custo: float) -> list[dict]:
    """Agentes consumindo >50% do custo total."""
    sugestoes: list[dict] = []
    for agente, dados in agg.items():
        if total_custo <= 0:
            continue
        pct = dados["custo_brl"] / total_custo * 100
        if pct > 50:
            sugestoes.append({
                "tipo": "AGENTE_VORAZ",
                "agente": agente,
                "modelo_atual": dados["model"],
                "economia_brl": round(dados["custo_brl"] * 0.3, 4),  # estimativa: otimizar reduz 30%
                "detalhe": (
                    f"{agente} consome {pct:.1f}% do custo total (R$ {dados['custo_brl']:.4f}). "
                    f"Considere chunking de prompt, caching de contexto, ou quebrar em sub-agentes."
                ),
                "severidade": "alta",
            })
        elif pct > 30:
            sugestoes.append({
                "tipo": "AGENTE_VORAZ",
                "agente": agente,
                "modelo_atual": dados["model"],
                "economia_brl": round(dados["custo_brl"] * 0.2, 4),
                "detalhe": (
                    f"{agente} consome {pct:.1f}% do custo total (R$ {dados['custo_brl']:.4f}). "
                    f"Monitorar se todas as chamadas são realmente necessárias."
                ),
                "severidade": "media",
            })
    return sorted(sugestoes, key=lambda x: x["economia_brl"], reverse=True)


def _detectar_erros_repetidos(agg: dict[str, dict]) -> list[dict]:
    """Agentes com alta taxa de finish_reason != STOP (erro, max_tokens, etc)."""
    sugestoes: list[dict] = []
    for agente, dados in agg.items():
        total_calls = dados["calls"]
        if total_calls < 5:
            continue
        erros = sum(v for k, v in dados["finish_reasons"].items() if k != "STOP")
        taxa_erro = erros / total_calls
        if taxa_erro > 0.20:
            custo_perdido = dados["custo_brl"] * taxa_erro
            sugestoes.append({
                "tipo": "ERRO_REPETIDO",
                "agente": agente,
                "modelo_atual": dados["model"],
                "economia_brl": round(custo_perdido, 4),
                "detalhe": (
                    f"{agente} tem {taxa_erro*100:.0f}% de chamadas com erro "
                    f"({erros}/{total_calls}). Principais: {dict(dados['finish_reasons'])}. "
                    f"Custo perdido estimado: R$ {custo_perdido:.4f}."
                ),
                "severidade": "alta" if taxa_erro > 0.50 else "media",
            })
    return sorted(sugestoes, key=lambda x: x["economia_brl"], reverse=True)


def _detectar_cache_geocoding(rows: list[dict]) -> list[dict]:
    """Chamadas repetidas de geocoding para a mesma cidade/bairro."""
    # O tokens_pipeline.csv pode não ter cidade/bairro; usamos uma heurística
    # baseada no agent_name a1_geoscout que faz geocoding
    sugestoes: list[dict] = []
    geo_calls = [r for r in rows if r.get("agent_name") == "a1_geoscout"]
    if len(geo_calls) > 10:
        # Se há muitas chamadas do geoscout, sugere cache
        custo_total = sum(compute_cost_brl(r.get("model"), int(r.get("tokens_in") or 0), int(r.get("tokens_out") or 0)) for r in geo_calls)
        estimativa_repeticao = 0.3  # assume 30% repetidas
        economia = custo_total * estimativa_repeticao
        if economia > 0.01:
            sugestoes.append({
                "tipo": "CACHE_GEOCODING",
                "agente": "a1_geoscout",
                "modelo_atual": "gemini-2.5-flash",
                "economia_brl": round(economia, 4),
                "detalhe": (
                    f"a1_geoscout fez {len(geo_calls)} chamadas nos últimos 30 dias "
                    f"(custo R$ {custo_total:.4f}). Cache de geocoding pode economizar "
                    f"~R$ {economia:.4f} ({estimativa_repeticao*100:.0f}% de repetição estimada)."
                ),
                "severidade": "media",
            })
    return sugestoes


def gerar_optimizacoes(dias: int = DEFAULT_DIAS) -> dict:
    """
    Gera relatório completo de otimizações.

    Retorna:
        {
            periodo_dias: int,
            total_chamadas: int,
            total_custo_brl: float,
            por_agente: { agente: {...} },
            sugestoes: [
                { tipo, agente, modelo_atual, modelo_sugerido?, economia_brl, detalhe, severidade }
            ],
            economia_total_estimada: float,
        }
    """
    rows = _ler_pipeline(dias)
    if not rows:
        return {
            "periodo_dias": dias,
            "total_chamadas": 0,
            "total_custo_brl": 0.0,
            "por_agente": {},
            "sugestoes": [],
            "economia_total_estimada": 0.0,
        }

    agg = _agregar_por_agente(rows)
    total_custo = sum(d["custo_brl"] for d in agg.values())
    total_calls = sum(d["calls"] for d in agg.values())

    sugestoes: list[dict] = []
    sugestoes.extend(_detectar_modelo_overpriced(agg))
    sugestoes.extend(_detectar_agente_voraz(agg, total_custo))
    sugestoes.extend(_detectar_erros_repetidos(agg))
    sugestoes.extend(_detectar_cache_geocoding(rows))

    # Deduplica sugestões do mesmo agente+tipo (pega a de maior economia)
    seen: set[str] = set()
    deduped: list[dict] = []
    for s in sorted(sugestoes, key=lambda x: x["economia_brl"], reverse=True):
        key = f"{s['tipo']}:{s['agente']}"
        if key not in seen:
            seen.add(key)
            deduped.append(s)

    economia_total = sum(s["economia_brl"] for s in deduped)

    # Resumo por agente limpo
    por_agente = {
        k: {
            "tokens_in": v["tokens_in"],
            "tokens_out": v["tokens_out"],
            "calls": v["calls"],
            "model": v["model"],
            "custo_brl": round(v["custo_brl"], 6),
            "finish_reasons": dict(v["finish_reasons"]),
        }
        for k, v in agg.items()
    }

    return {
        "periodo_dias": dias,
        "total_chamadas": total_calls,
        "total_custo_brl": round(total_custo, 6),
        "por_agente": por_agente,
        "sugestoes": deduped,
        "economia_total_estimada": round(economia_total, 4),
    }
