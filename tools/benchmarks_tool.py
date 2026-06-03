"""
tools/benchmarks_tool.py — benchmarks setoriais fitness BR via Search Grounding.

Em vez de hardcodar valores ACAD 2024 que viram defasados, este módulo
consulta Gemini + Search Grounding pra extrair indicadores atualizados do
Panorama Setorial Fitness Brasil mais recente.

Cache em 2 níveis:
  1. Memory cache (processo) — `_MEM_CACHE`. Zera em restart.
  2. File cache `metrics/cache/benchmarks_setoriais.json` — TTL 7 dias.

Fallback: se Search Grounding falhar ou retornar inválido, retorna os
defaults ACAD 2024 com `fonte: "fallback_acad_2024"`. **Pipeline NUNCA
falha por causa de benchmark indisponível.**

Uso típico (sync, idempotente):
    from tools.benchmarks_tool import obter_benchmarks_setoriais
    b = obter_benchmarks_setoriais()
    ticket_low = b["ticket_por_modelo"]["low"]   # número (R$)
    inadimpl = b["inadimplencia_com_recorrencia"]  # 0.04 (4%)
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CACHE_DIR = Path(__file__).resolve().parent.parent / "metrics" / "cache"
CACHE_PATH = CACHE_DIR / "benchmarks_setoriais.json"
SNAPSHOT_PATH = CACHE_DIR / "benchmark_snapshots.json"
TTL_SEGUNDOS = 7 * 86400  # 7 dias

# Fallback ACAD 2024 + ajustes Panorama 2025 (do que coletamos manualmente).
# Quando Search Grounding funciona, esses valores são substituídos.
DEFAULTS_FALLBACK: dict[str, Any] = {
    "ticket_por_modelo": {
        "low": 79.90,
        "mid": 119.90,
        "premium": 199.90,
        "boutique": 249.90,
        "crossfit": 289.90,
    },
    "inadimplencia_com_recorrencia": 0.04,
    "inadimplencia_sem_recorrencia": 0.20,
    "inadimplencia_por_modelo": {
        "low": 0.05,
        "mid": 0.04,
        "premium": 0.025,
    },
    "churn_anual": 0.28,
    "churn_mensal_por_modelo": {
        "low": 0.10,
        "mid": 0.07,
        "premium": 0.04,
    },
    "academias_ativas_brasil": 41_332,
    "frequencia_semanal_aluno": 2.2,
    "fonte": "fallback_acad_2024_panorama_2025_manual",
    "data_coleta": "2026-05-12",
    "versao_cache": "v1.0",
}


_MEM_CACHE: dict[str, Any] | None = None

# Faixas ACAD/Panorama — valores fora disso são alucinação comum do Grounding
# (ex.: premium R$ 1.500 confundido com plano anual ou boutique internacional).
TICKET_SANITY_BANDS: dict[str, tuple[float, float]] = {
    "low": (59.0, 139.0),
    "mid": (109.0, 279.0),
    "premium": (179.0, 599.0),
    "boutique": (199.0, 799.0),
    "crossfit": (129.0, 449.0),
}

TICKET_SANITY_DEFAULTS: dict[str, float] = {
    "low": 89.90,
    "mid": 149.90,
    "premium": 299.90,
    "boutique": float(DEFAULTS_FALLBACK["ticket_por_modelo"]["boutique"]),
    "crossfit": float(DEFAULTS_FALLBACK["ticket_por_modelo"]["crossfit"]),
}


def sanitizar_ticket_por_modelo(
    tickets: dict[str, Any],
) -> tuple[dict[str, float], list[str]]:
    """
    Normaliza ticket_por_modelo vindo de Search Grounding ou snapshot batch.
    Retorna (tickets_limpos, avisos).
    """
    avisos: list[str] = []
    limpos: dict[str, float] = {}
    for key, raw in (tickets or {}).items():
        if key not in TICKET_SANITY_BANDS:
            continue
        try:
            val = float(raw)
        except (TypeError, ValueError):
            avisos.append(f"ticket {key} inválido ({raw!r}) — fallback ACAD")
            limpos[key] = TICKET_SANITY_DEFAULTS[key]
            continue
        lo, hi = TICKET_SANITY_BANDS[key]
        if val < lo or val > hi:
            fallback = TICKET_SANITY_DEFAULTS[key]
            avisos.append(
                f"ticket {key} R${val:.0f} fora da banda ACAD "
                f"(R${lo:.0f}–R${hi:.0f}) — usando R${fallback:.2f}"
            )
            limpos[key] = fallback
        else:
            limpos[key] = round(val, 2)
    return limpos, avisos


def _sanitizar_benchmark_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Aplica sanitização de tickets in-place lógica; preserva demais campos."""
    out = dict(data)
    tpm = out.get("ticket_por_modelo")
    if isinstance(tpm, dict):
        limpos, avisos = sanitizar_ticket_por_modelo(tpm)
        out["ticket_por_modelo"] = limpos
        if avisos:
            out["ticket_sanity_avisos"] = avisos
    return out


def _ler_snapshot_arquivo() -> dict | None:
    """Snapshot unificado (setorial + sector_listed) do batch."""
    if not SNAPSHOT_PATH.exists():
        return None
    try:
        data = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        ts_raw = data.get("gerado_em") or data.get("_cached_at_iso")
        if not ts_raw:
            return None
        from datetime import datetime, timezone

        ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - ts.astimezone(timezone.utc)
        if age.total_seconds() > TTL_SEGUNDOS:
            return None
        return data
    except Exception:
        return None


def _ler_cache_arquivo() -> dict | None:
    if not CACHE_PATH.exists():
        return None
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        ts = data.get("_cached_at_ts", 0)
        if time.time() - ts > TTL_SEGUNDOS:
            return None
        return data
    except Exception:
        return None


def _salvar_cache_arquivo(data: dict) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {**data, "_cached_at_ts": time.time(),
                   "_cached_at_iso": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        CACHE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass  # nunca bloqueia pipeline por falha de cache


def _buscar_via_grounding() -> dict | None:
    """Consulta Gemini com Search Grounding pra extrair benchmarks.

    Retorna dict no shape de DEFAULTS_FALLBACK ou None se falhar.
    """
    try:
        from google.genai import types
        from tools._genai_client import build_genai_client, generate_content_resilient

        client = build_genai_client()

        query = (
            "Considerando o Panorama Setorial Fitness Brasil mais recente "
            "(Fitness Brasil/HFA - antigo IHRSA Brasil) e dados ACAD Brasil, "
            "responda em JSON puro (sem markdown, sem texto antes/depois) "
            "com os seguintes campos numéricos atuais para o mercado fitness brasileiro:\n"
            "{\n"
            '  "ticket_por_modelo": {"low": <reais>, "mid": <reais>, "premium": <reais>, "boutique": <reais>, "crossfit": <reais>},\n'
            '  "inadimplencia_com_recorrencia": <fração decimal, ex 0.04>,\n'
            '  "inadimplencia_sem_recorrencia": <fração decimal, ex 0.20>,\n'
            '  "churn_anual": <fração decimal>,\n'
            '  "academias_ativas_brasil": <inteiro>,\n'
            '  "frequencia_semanal_aluno": <decimal>,\n'
            '  "fonte": "<nome do relatório principal + ano>",\n'
            '  "data_coleta": "<ISO date>"\n'
            "}\n"
            "Use valores típicos de mercado de 2025-2026. Não invente; use a busca."
        )

        resp = generate_content_resilient(
            client,
            model="gemini-2.5-flash",
            contents=query,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
            max_retries=3,
            base_delay=4.0,
        )
        text = (resp.text or "").strip()
        # Remove cercas markdown caso o modelo tenha incluído
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip().rstrip("`").strip()

        parsed = json.loads(text)
        if not isinstance(parsed, dict) or "ticket_por_modelo" not in parsed:
            return None
        # Mescla com defaults pra não perder chaves opcionais
        merged = {**DEFAULTS_FALLBACK, **parsed}
        merged["fonte"] = parsed.get("fonte") or "search_grounding_panorama_2025"
        merged["data_coleta"] = parsed.get("data_coleta") or datetime.now(timezone.utc).date().isoformat()
        return _sanitizar_benchmark_payload(merged)
    except Exception as e:
        print(f"[benchmarks_tool] falha no Search Grounding: {type(e).__name__}: {e}")
        return None


def obter_benchmarks_setoriais(force_refresh: bool = False) -> dict:
    """
    Retorna o dict de benchmarks atualizados. Idempotente, seguro pra chamar
    em loop quente. Cache 7d em disco + memória.

    `force_refresh=True` ignora todos os caches e busca de novo (debug).
    """
    global _MEM_CACHE

    if not force_refresh:
        if _MEM_CACHE is not None:
            return _MEM_CACHE
        snap = _ler_snapshot_arquivo()
        if snap and isinstance(snap.get("setorial"), dict):
            setorial = _sanitizar_benchmark_payload(snap["setorial"])
            _MEM_CACHE = setorial
            return setorial
        file_cache = _ler_cache_arquivo()
        if file_cache is not None:
            file_cache = _sanitizar_benchmark_payload(file_cache)
            _MEM_CACHE = file_cache
            return file_cache

    # Tentar Search Grounding
    encontrado = _buscar_via_grounding()
    if encontrado is None:
        _MEM_CACHE = DEFAULTS_FALLBACK
        return DEFAULTS_FALLBACK

    encontrado = _sanitizar_benchmark_payload(encontrado)
    _salvar_cache_arquivo(encontrado)
    _MEM_CACHE = encontrado
    return encontrado


def reset_cache() -> None:
    """Limpa caches (memory + disco). Útil em testes."""
    global _MEM_CACHE
    _MEM_CACHE = None
    if CACHE_PATH.exists():
        try:
            CACHE_PATH.unlink()
        except Exception:
            pass
