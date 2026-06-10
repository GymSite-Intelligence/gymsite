#!/usr/bin/env python3
"""
Eval mínimo do Golden Dataset — GymSite Intelligence.

Uso:
  python eval/run_eval.py
  python eval/run_eval.py --case fortaleza_parangaba_20260528
  python eval/run_eval.py --with-positioning   # nightly / manual (LLM)
  python eval/run_eval.py --cno-only           # apenas CNO (legado)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from eval.evaluators.cno_consistency_eval import evaluate_cno_consistency
from eval.evaluators.financial_consistency_eval import evaluate_financial_consistency
from eval.evaluators.positioning_quality_eval import evaluate_positioning_quality
from eval.evaluators.structural_eval import evaluate_structural_consistency


def _load_case(case_dir: Path) -> tuple[dict, dict, dict[str, Any]]:
    golden = json.loads((case_dir / "expected_output.json").read_text(encoding="utf-8"))
    report = json.loads((case_dir / "full_report.json").read_text(encoding="utf-8"))
    supplement: dict[str, Any] = {}
    for name in ("cno_cruzamento_cnpj.json", "cno_live.json"):
        path = case_dir / name
        if path.is_file():
            supplement[name] = json.loads(path.read_text(encoding="utf-8"))
    return golden, report, supplement


def _pack_result(result) -> dict[str, Any]:
    return {
        "status": result.status,
        "reason": result.reason,
        "issues": result.issues,
    }


def run_case(
    case_dir: Path,
    *,
    with_positioning: bool,
    with_structural: bool,
    with_financial: bool,
) -> dict:
    golden, report, supplement = _load_case(case_dir)
    cno = evaluate_cno_consistency(report, golden, supplement=supplement or None)
    out: dict[str, Any] = {
        "case_id": golden.get("case_id", case_dir.name),
        "approved": golden.get("approved", False),
        "cno": _pack_result(cno),
    }
    if with_structural:
        out["structural"] = _pack_result(evaluate_structural_consistency(report, golden))
    if with_financial:
        out["financial"] = _pack_result(evaluate_financial_consistency(report, golden))
    if with_positioning:
        out["positioning"] = _pack_result(evaluate_positioning_quality(report, golden))
    return out


def _print_issues(prefix: str, issues: list[dict]) -> None:
    for issue in issues:
        field = issue.get("field", "")
        msg = issue.get("message", issue.get("reason", ""))
        suffix = f" ({field})" if field else ""
        print(f"      • {prefix} {msg}{suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Golden dataset eval")
    parser.add_argument("--dataset", default="eval/golden_dataset")
    parser.add_argument("--case", help="case_id ou nome de pasta")
    parser.add_argument(
        "--with-positioning",
        action="store_true",
        help="Inclui PositioningQualityEval (LLM; requer GOOGLE_API_KEY)",
    )
    parser.add_argument(
        "--cno-only",
        action="store_true",
        help="Apenas CNO (sem structural/financial)",
    )
    parser.add_argument(
        "--bundle-a0-gate",
        action="store_true",
        help="Fase C: roda golden_bundle_a0_gate (A0_CONTEXT_SOURCE=ckan_bundle) e sai",
    )
    args = parser.parse_args()

    if args.bundle_a0_gate:
        from scripts.batch.golden_bundle_a0_gate import main as bundle_gate_main

        return bundle_gate_main()

    with_structural = not args.cno_only
    with_financial = not args.cno_only

    dataset = ROOT / args.dataset
    if args.case:
        dirs = [dataset / args.case]
    else:
        dirs = sorted(
            p for p in dataset.iterdir()
            if p.is_dir() and (p / "expected_output.json").is_file()
        )

    icons = {"PASS": "OK", "WARN": "!!", "FAIL": "XX", "SKIP": "--"}
    results = []
    fail_counts = {"cno": 0, "structural": 0, "financial": 0, "positioning": 0}

    for d in dirs:
        if not d.exists():
            print(f"SKIP {args.case}: pasta não encontrada")
            return 1
        r = run_case(
            d,
            with_positioning=args.with_positioning,
            with_structural=with_structural,
            with_financial=with_financial,
        )
        results.append(r)
        parts = [f"[{icons.get(r['cno']['status'], '?')}] {r['case_id']}"]
        parts.append(f"CNO {r['cno']['status']}")
        if with_structural:
            st = r["structural"]["status"]
            parts.append(f"STR {icons.get(st, '?')} {st}")
        if with_financial:
            fin = r["financial"]["status"]
            parts.append(f"FIN {icons.get(fin, '?')} {fin}")
        if args.with_positioning:
            pos_st = r["positioning"]["status"]
            parts.append(f"POS {icons.get(pos_st, '?')} {pos_st}")
        print(" — ".join(parts))

        _print_issues("CNO", r["cno"]["issues"])
        if with_structural and r["structural"]["issues"]:
            _print_issues("STR", r["structural"]["issues"])
        if with_financial and r["financial"]["issues"]:
            _print_issues("FIN", r["financial"]["issues"])
        if args.with_positioning and r["positioning"]["issues"]:
            _print_issues("POS", r["positioning"]["issues"])

        for key in fail_counts:
            block = r.get(key)
            if block and block.get("status") == "FAIL":
                fail_counts[key] += 1

    summary = f"\n{len(results)} casos | CNO FAIL: {fail_counts['cno']}"
    if with_structural:
        summary += f" | STR FAIL: {fail_counts['structural']}"
    if with_financial:
        summary += f" | FIN FAIL: {fail_counts['financial']}"
    if args.with_positioning:
        summary += f" | POS FAIL: {fail_counts['positioning']}"
    print(summary)

    gate_fail = fail_counts["cno"]
    if with_structural:
        gate_fail += fail_counts["structural"]
    if with_financial:
        gate_fail += fail_counts["financial"]
    if args.with_positioning:
        gate_fail += fail_counts["positioning"]
    return 1 if gate_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
