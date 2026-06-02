"""
PositioningQualityEval — LLM-as-judge para posicionamento_estrategico (A9).

Uso: nightly / manual (`python eval/run_eval.py --with-positioning`).
Não é gate de PR (custo + flake).
"""
from __future__ import annotations

import json
import os
import time
from typing import Any

from eval.evaluators.base import EvalResult

_MODEL = os.getenv("POSITIONING_EVAL_MODEL", "gemini-2.0-flash")
_MAX_RETRIES = int(os.getenv("POSITIONING_EVAL_RETRIES", "3"))
_PASS_SCORE = float(os.getenv("POSITIONING_EVAL_PASS_SCORE", "7"))


def _has_llm_credentials() -> bool:
    if os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in ("1", "true", "yes"):
        return bool(os.getenv("GOOGLE_CLOUD_PROJECT", "").strip())
    return bool(
        (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    )


def _extract_posicionamento(report: dict) -> dict | None:
    oc = report.get("output_consolidado") or report
    if not isinstance(oc, dict):
        return None
    pos = oc.get("posicionamento_estrategico")
    return pos if isinstance(pos, dict) and pos else None


def _call_judge(
    pos: dict,
    *,
    veredito_base: str | None,
    score_top1: float | None,
) -> dict[str, Any]:
    from google.genai import types

    from tools._genai_client import build_genai_client

    prompt = f"""Você audita saídas do agente A9 (posicionamento ERRC) do GymSite Intelligence.

Critérios (nota 0–10):
1. framework_errc com quatro listas (eliminar/reduzir/aumentar/criar) não triviais
2. gaps_identificados acionáveis (≥1 item)
3. recomendacao_ticket com ticket_recomendado numérico e justificativa
4. veredito_posicionamento ∈ {{OCEANO_AZUL, TRANSICAO, VERMELHO}}
5. Coerência com veredito/score do relatório base

Contexto do relatório base:
- veredito: {veredito_base or "desconhecido"}
- score_top1: {score_top1}

Posicionamento (JSON):
{json.dumps(pos, ensure_ascii=False)[:14000]}

Responda SOMENTE JSON:
{{"score": <0-10>, "pass": <bool>, "issues": ["..."], "reason": "..."}}
Use pass=true se score >= {_PASS_SCORE}.
"""

    client = build_genai_client()
    resp = client.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )
    raw = (resp.text or "").strip()
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("judge retornou JSON não-objeto")
    return parsed


def evaluate_positioning_quality(report: dict, golden: dict) -> EvalResult:
    pos = _extract_posicionamento(report)
    if not pos:
        return EvalResult(
            status="SKIP",
            evaluator="positioning_quality",
            reason="sem posicionamento_estrategico no full_report",
        )

    if not _has_llm_credentials():
        return EvalResult(
            status="SKIP",
            evaluator="positioning_quality",
            reason="credenciais Gemini/Vertex ausentes",
        )

    veredito_base = golden.get("expected_veredito")
    score_top1 = golden.get("expected_score_top1")
    last_err: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            parsed = _call_judge(
                pos,
                veredito_base=veredito_base,
                score_top1=score_top1,
            )
            score = float(parsed.get("score", 0))
            passed = bool(parsed.get("pass", score >= _PASS_SCORE))
            issues = [
                {"field": "positioning", "message": str(m)}
                for m in (parsed.get("issues") or [])
            ]
            return EvalResult(
                status="PASS" if passed else "FAIL",
                evaluator="positioning_quality",
                reason=str(parsed.get("reason") or ""),
                issues=issues,
            )
        except Exception as exc:
            last_err = exc
            if attempt < _MAX_RETRIES:
                time.sleep(min(2**attempt, 8))

    return EvalResult(
        status="FAIL",
        evaluator="positioning_quality",
        reason=f"judge falhou após {_MAX_RETRIES} tentativas: {last_err}",
    )
