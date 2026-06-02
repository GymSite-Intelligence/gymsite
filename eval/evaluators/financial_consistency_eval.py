"""
Consistência financeira e de veredito vs. golden case.

Regras determinísticas (sem LLM): coerência veredito×score, modelo recomendado,
faixas de ticket por tier (mercado BR validado jun/2026).
"""
from __future__ import annotations

from typing import Any

from eval.evaluators.base import EvalResult

# Ticket nominal mensal estrutural por cenário (pós-promo 1º mês) — HANDOFF jun/2026
_MODEL_TICKET_BANDS: dict[str, tuple[float, float]] = {
    "low cost": (79.0, 129.0),
    "mid market": (129.0, 169.0),
    "premium": (159.0, 450.0),
    "nenhum": (0.0, 0.0),
}

def _output_block(report: dict) -> dict:
    oc = report.get("output_consolidado") or report
    return oc if isinstance(oc, dict) else {}


def _float_or_none(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _norm_modelo(v: Any) -> str:
    return str(v or "").strip().lower()


def _expected_veredito_from_score(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= 8.0:
        return "APROVADO"
    if score >= 6.0:
        return "APROVADO COM RESSALVAS"
    if score >= 4.0:
        return "INVESTIGAR MAIS"
    return "REPROVADO"


def _extract_scenario_tickets(oc: dict) -> dict[str, float]:
    """Lê tickets nominais dos cenários A4 quando presentes no JSON."""
    out: dict[str, float] = {}
    cenarios = oc.get("viabilidade_3_cenarios") or oc.get("cenarios")
    if not isinstance(cenarios, dict):
        return out

    key_map = {
        "low": "low cost",
        "low_cost": "low cost",
        "mid": "mid market",
        "mid market": "mid market",
        "premium": "premium",
    }
    for raw_key, band in key_map.items():
        block = cenarios.get(raw_key)
        if not isinstance(block, dict):
            continue
        for ticket_key in ("ticket_nominal", "ticket", "ticket_mensal"):
            val = _float_or_none(block.get(ticket_key))
            if val is not None:
                out[band] = val
                break
    return out


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


def evaluate_financial_consistency(report: dict, golden: dict) -> EvalResult:
    cfg = golden.get("financial_validation") or {}
    if cfg.get("required") is False:
        return EvalResult(
            status="SKIP",
            evaluator="financial",
            reason="financial_validation.required=false",
        )

    issues: list[dict[str, Any]] = []
    oc = _output_block(report)
    if not oc:
        return EvalResult(
            status="FAIL",
            evaluator="financial",
            reason="output_consolidado ausente",
        )

    veredito = str(oc.get("veredito") or golden.get("expected_veredito") or "").strip().upper()
    score_top1 = _float_or_none(oc.get("score_top1_candidato"))
    expected_veredito = str(golden.get("expected_veredito") or "").strip().upper()

    if expected_veredito and veredito and veredito != expected_veredito:
        issues.append(
            {
                "field": "veredito",
                "expected": expected_veredito,
                "actual": veredito,
                "message": "Veredito diverge do golden",
                "severity": "fail",
            }
        )

    inferred = _expected_veredito_from_score(score_top1)
    if score_top1 is not None and inferred and veredito:
        if veredito == "APROVADO" and score_top1 < 8.0:
            issues.append(
                {
                    "field": "veredito_vs_score",
                    "message": f"APROVADO com score_top1={score_top1} (< 8.0)",
                    "severity": "fail",
                }
            )
        elif veredito == "APROVADO COM RESSALVAS" and score_top1 < 6.0:
            issues.append(
                {
                    "field": "veredito_vs_score",
                    "message": f"APROVADO COM RESSALVAS com score_top1={score_top1} (< 6.0)",
                    "severity": "fail",
                }
            )
        elif veredito == "INVESTIGAR MAIS" and score_top1 >= 8.0:
            issues.append(
                {
                    "field": "veredito_vs_score",
                    "message": f"INVESTIGAR MAIS com score_top1 alto ({score_top1})",
                    "severity": "warn",
                }
            )
        elif veredito == "REPROVADO" and score_top1 >= 6.0:
            issues.append(
                {
                    "field": "veredito_vs_score",
                    "message": f"REPROVADO com score_top1={score_top1} (>= 6.0)",
                    "severity": "warn",
                }
            )

    modelo = _norm_modelo(oc.get("modelo_recomendado"))
    expected_modelo = _norm_modelo(golden.get("expected_modelo_recomendado"))
    if expected_modelo and modelo and modelo != expected_modelo:
        issues.append(
            {
                "field": "modelo_recomendado",
                "expected": expected_modelo,
                "actual": modelo,
                "message": "Modelo diverge do golden",
                "severity": "fail",
            }
        )

    if veredito.startswith("APROVADO") and modelo in ("", "nenhum", "none"):
        issues.append(
            {
                "field": "modelo_recomendado",
                "message": "Veredito positivo sem modelo_recomendado",
                "severity": "warn",
            }
        )

    tolerances = golden.get("tolerance_fields") or {}
    aluguel_tol = tolerances.get("aluguel_mensal")
    if aluguel_tol is not None:
        exp_aluguel = _float_or_none(golden.get("expected_aluguel_mensal"))
        act_aluguel = _float_or_none(oc.get("aluguel_mensal"))
        if exp_aluguel is not None and act_aluguel is not None:
            rel = abs(act_aluguel - exp_aluguel) / max(exp_aluguel, 1.0)
            if rel > float(aluguel_tol):
                issues.append(
                    {
                        "field": "aluguel_mensal",
                        "expected": exp_aluguel,
                        "actual": act_aluguel,
                        "message": f"Aluguel fora da tolerância relativa {aluguel_tol:.0%}",
                        "severity": "warn",
                    }
                )

    tickets = _extract_scenario_tickets(oc)
    if tickets and modelo in _MODEL_TICKET_BANDS and modelo != "nenhum":
        lo, hi = _MODEL_TICKET_BANDS[modelo]
        ticket_ref = tickets.get(modelo)
        if ticket_ref is not None:
            if ticket_ref < lo * 0.85 or ticket_ref > hi * 1.35:
                issues.append(
                    {
                        "field": "ticket_vs_modelo",
                        "message": (
                            f"Ticket cenário {ticket_ref:.0f} incompatível com modelo "
                            f"{modelo.title()} (faixa {lo:.0f}–{hi:.0f})"
                        ),
                        "severity": "fail",
                    }
                )

    score_viab = _float_or_none(
        (oc.get("scores_regionais") or {}).get("viabilidade")
        if isinstance(oc.get("scores_regionais"), dict)
        else oc.get("score_viabilidade")
    )
    if score_viab is not None and score_viab < 5.0 and veredito == "APROVADO":
        issues.append(
            {
                "field": "score_viabilidade",
                "message": f"APROVADO com viabilidade regional baixa ({score_viab})",
                "severity": "warn",
            }
        )

    status = _finalize_status(issues)
    return EvalResult(status=status, evaluator="financial", issues=issues)
