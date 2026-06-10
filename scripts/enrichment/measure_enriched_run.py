#!/usr/bin/env python3
"""Mede pipeline enrichment: cache deterministico -> prompt comprimido -> LLM minimo."""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ENRICHMENT_DIR = Path(__file__).resolve().parent
if str(ENRICHMENT_DIR) not in sys.path:
    sys.path.insert(0, str(ENRICHMENT_DIR))

METRICS_PATH = ENRICHMENT_DIR / "production_run_metrics.json"
DEFAULT_MODEL = "gemini-2.5-flash-lite"


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
        load_dotenv(ROOT / "gymsite_intelligence" / ".env", override=False)
    except ImportError:
        pass


def _llm_available() -> bool:
    import os

    if os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true":
        return bool(os.getenv("GOOGLE_CLOUD_PROJECT", "").strip())
    key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    return bool(key) and not key.startswith("AQ.")


def llm_call_fn(prompt: str, *, model: str = DEFAULT_MODEL) -> dict:
    """Chamada LLM minima; retorna texto + usage + custo estimado."""
    from tools._genai_client import build_genai_client
    from tools.pricing import compute_cost_brl
    from tools.token_telemetry import _extract_usage

    client = build_genai_client()
    instruction = (
        "Voce recebe contexto local pre-coletado (cache). "
        "Responda EXATAMENTE neste formato (4 linhas):\n"
        "Viabilidade: [ALTA/MEDIA/BAIXA] - [motivo em 1 frase]\n"
        "Concorrencia: [N] unidades ([redes]) - [saturacao: BAIXA/MEDIA/ALTA]\n"
        "Aluguel: mediana R$[X]/m2 - [competitivo/abaixo/acima do mercado]\n"
        "Recomendacao: [1 frase comercial objetiva]\n"
        "Nao invente dados. Use apenas o bloco fornecido.\n\n"
    )
    t0 = time.perf_counter()
    resp = client.models.generate_content(
        model=model,
        contents=instruction + prompt,
    )
    elapsed = time.perf_counter() - t0
    usage = _extract_usage(resp)
    tokens_in = int(usage.get("tokens_in") or 0)
    tokens_out = int(usage.get("tokens_out") or 0)
    custo = compute_cost_brl(model, tokens_in, tokens_out)
    text = (getattr(resp, "text", None) or "").strip()
    return {
        "ok": True,
        "model": model,
        "tempo_llm_segundos": round(elapsed, 3),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "tokens_total": int(usage.get("tokens_total") or tokens_in + tokens_out),
        "usage_fonte": usage.get("fonte"),
        "custo_brl": round(custo, 6),
        "resposta_chars": len(text),
        "resposta_preview": text[:200],
    }


def run_measurement(
    cidade: str,
    bairro: str,
    uf: str,
    *,
    area_min: int = 800,
    area_max: int = 1500,
    skip_llm: bool = False,
    model: str = DEFAULT_MODEL,
) -> dict:
    from cache_enrichment import build_cache
    from prompt_compressor import compress_from_cache

    started = datetime.now(timezone.utc).isoformat()
    t_all = time.perf_counter()

    t0 = time.perf_counter()
    cache = build_cache(cidade, bairro, uf, area_min, area_max)
    tempo_cache = time.perf_counter() - t0

    t0 = time.perf_counter()
    prompt = compress_from_cache(cache)
    tempo_compress = time.perf_counter() - t0

    llm: dict = {"ok": False, "skipped": True}
    if not skip_llm and _llm_available():
        try:
            llm = llm_call_fn(prompt, model=model)
            llm["skipped"] = False
        except Exception as exc:
            llm = {"ok": False, "skipped": False, "error": str(exc)}
    elif skip_llm:
        llm = {"ok": False, "skipped": True, "motivo": "--skip-llm"}
    else:
        llm = {
            "ok": False,
            "skipped": True,
            "motivo": "GEMINI_API_KEY/Vertex nao configurado",
        }

    tempo_total = time.perf_counter() - t_all
    tokens_in = int(llm.get("tokens_in") or 0) if llm.get("ok") else 0
    custo_llm = float(llm.get("custo_brl") or 0.0) if llm.get("ok") else 0.0

    metrics = {
        "gerado_em": started,
        "local": {"cidade": cidade, "bairro": bairro, "uf": uf},
        "cache_key": cache.get("cache_key"),
        "tempo_execucao_segundos": round(tempo_total, 3),
        "tempo_cache_segundos": round(tempo_cache, 3),
        "tempo_compress_segundos": round(tempo_compress, 3),
        "tempo_llm_segundos": round(float(llm.get("tempo_llm_segundos") or 0.0), 3),
        "prompt_chars": len(prompt),
        "tokens_in_total": tokens_in,
        "tokens_out_total": int(llm.get("tokens_out") or 0) if llm.get("ok") else 0,
        "custo_total_brl": round(custo_llm, 6),
        "custo_nota": (
            "Somente LLM (pricing.py); cache deterministico sem custo tokenizado"
            if llm.get("ok")
            else "0 — LLM nao executado; ver llm"
        ),
        "llm": llm,
        "competicao_osm_unidades": cache.get("competicao_osm_unidades")
        or (cache.get("competicao_local") or {}).get("total_unidades_osm"),
        "aluguel_n_validos": (cache.get("aluguel_portais") or {}).get("n_validos"),
    }
    return metrics


def main() -> int:
    _load_env()
    p = argparse.ArgumentParser(description="Mede run enrichment em producao (cache+compress+LLM)")
    p.add_argument("--cidade", default="Fortaleza")
    p.add_argument("--bairro", default="Meireles")
    p.add_argument("--uf", default="CE")
    p.add_argument("--area-min", type=int, default=800)
    p.add_argument("--area-max", type=int, default=1500)
    p.add_argument("--skip-llm", action="store_true")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--out", default=str(METRICS_PATH))
    args = p.parse_args()

    metrics = run_measurement(
        args.cidade,
        args.bairro,
        args.uf,
        area_min=args.area_min,
        area_max=args.area_max,
        skip_llm=args.skip_llm,
        model=args.model,
    )
    out = Path(args.out)
    out.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=== measure_enriched_run ===")
    print("tempo_execucao_segundos:", metrics["tempo_execucao_segundos"])
    print("tokens_in_total:", metrics["tokens_in_total"])
    print("custo_total_brl:", metrics["custo_total_brl"])
    print("prompt_chars:", metrics["prompt_chars"])
    print("llm:", json.dumps(metrics["llm"], ensure_ascii=False))
    print("written:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
