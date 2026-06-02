"""
Validação estrutural do JSON canônico vs. golden case.

Compara `output_consolidado` do full_report com `expected_output.json`:
campos críticos, tolerâncias numéricas, input e scores regionais.
"""
from __future__ import annotations

from typing import Any

from eval.evaluators.base import EvalResult

_PLACEHOLDER_STRINGS = frozenset(
    {"", "?", "n/a", "na", "none", "null", "dados_nao_disponiveis", "dados não disponíveis"}
)

_CRITICAL_TO_GOLDEN = {
    "veredito": "expected_veredito",
    "score_top1_candidato": "expected_score_top1",
    "modelo_recomendado": "expected_modelo_recomendado",
    "nivel_saturacao": "expected_nivel_saturacao",
    "score_bairro": "expected_score_bairro",
}


def _output_block(report: dict) -> dict:
    oc = report.get("output_consolidado") or report
    return oc if isinstance(oc, dict) else {}


def _input_block(report: dict) -> dict:
    inp = report.get("input_canonico") or {}
    return inp if isinstance(inp, dict) else {}


def _norm_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _is_missing_expected(v: Any) -> bool:
    s = _norm_str(v).lower()
    return s in _PLACEHOLDER_STRINGS


def _float_or_none(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _finalize_status(issues: list[dict[str, Any]]) -> str:
    fails = [i for i in issues if i.get("severity", "fail") != "warn"]
    warns = [i for i in issues if i.get("severity") == "warn"]
    if not issues:
        return "PASS"
    if fails:
        return "WARN" if len(fails) <= 2 else "FAIL"
    if warns:
        return "WARN"
    return "PASS"


def evaluate_structural_consistency(report: dict, golden: dict) -> EvalResult:
    cfg = golden.get("structural_validation") or {}
    if cfg.get("required") is False:
        return EvalResult(
            status="SKIP",
            evaluator="structural",
            reason="structural_validation.required=false",
        )

    issues: list[dict[str, Any]] = []
    oc = _output_block(report)
    if not oc:
        return EvalResult(
            status="FAIL",
            evaluator="structural",
            reason="output_consolidado ausente no full_report",
        )

    inp_golden = golden.get("input_canonico") or {}
    inp_report = _input_block(report)
    for key in ("cidade", "bairro", "uf"):
        exp = _norm_str(inp_golden.get(key))
        act = _norm_str(inp_report.get(key))
        if exp and act and exp.lower() != act.lower():
            issues.append(
                {
                    "field": f"input_canonico.{key}",
                    "expected": exp,
                    "actual": act,
                    "message": "Input do relatório diverge do golden",
                    "severity": "fail",
                }
            )

    critical = golden.get("critical_fields") or list(_CRITICAL_TO_GOLDEN.keys())
    tolerances = golden.get("tolerance_fields") or {}

    for field in critical:
        golden_key = _CRITICAL_TO_GOLDEN.get(field, f"expected_{field}")
        expected = golden.get(golden_key)
        actual = oc.get(field)

        if _is_missing_expected(expected):
            continue

        tol = tolerances.get(field)
        exp_f = _float_or_none(expected)
        act_f = _float_or_none(actual)

        if exp_f is not None and act_f is not None and tol is not None:
            if abs(act_f - exp_f) > float(tol):
                issues.append(
                    {
                        "field": field,
                        "expected": exp_f,
                        "actual": act_f,
                        "message": f"Fora da tolerância ±{tol}",
                        "severity": "fail",
                    }
                )
            continue

        if _norm_str(expected).lower() != _norm_str(actual).lower():
            issues.append(
                {
                    "field": field,
                    "expected": expected,
                    "actual": actual,
                    "message": "Campo crítico divergente",
                    "severity": "fail",
                }
            )

    scores = oc.get("scores_regionais") or {}
    if not isinstance(scores, dict):
        scores = {}
    for dim in ("demografico", "viabilidade"):
        if scores.get(dim) is None and oc.get(f"score_{dim}") is None:
            issues.append(
                {
                    "field": f"scores_regionais.{dim}",
                    "message": f"Score regional '{dim}' ausente",
                    "severity": "warn",
                }
            )
    has_concorrencia = (
        scores.get("concorrencia") is not None
        or scores.get("competitivo") is not None
        or oc.get("score_concorrencia") is not None
        or oc.get("score_competitivo") is not None
    )
    if not has_concorrencia:
        issues.append(
            {
                "field": "scores_regionais.concorrencia",
                "message": "Score de concorrência ausente",
                "severity": "warn",
            }
        )

    count_tol = int(cfg.get("count_tolerance", golden.get("count_tolerance", 2)))
    expected_cand = golden.get("candidatos_count")
    if expected_cand is not None:
        actual_cand = len(oc.get("top_3_candidatos") or [])
        if abs(actual_cand - int(expected_cand)) > count_tol:
            issues.append(
                {
                    "field": "candidatos_count",
                    "expected": expected_cand,
                    "actual": actual_cand,
                    "message": f"Top candidatos fora da tolerância ±{count_tol}",
                    "severity": "warn",
                }
            )

    expected_comp = golden.get("competidores_count")
    if expected_comp is not None:
        actual_comp = oc.get("total_concorrentes_analisados")
        if actual_comp is None:
            actual_comp = 0
        try:
            if abs(int(actual_comp) - int(expected_comp)) > count_tol:
                issues.append(
                    {
                        "field": "competidores_count",
                        "expected": expected_comp,
                        "actual": actual_comp,
                        "message": f"Concorrentes fora da tolerância ±{count_tol}",
                        "severity": "warn",
                    }
                )
        except (TypeError, ValueError):
            pass

    status = _finalize_status(issues)
    return EvalResult(status=status, evaluator="structural", issues=issues)
