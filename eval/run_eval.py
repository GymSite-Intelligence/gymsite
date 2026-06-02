#!/usr/bin/env python3
"""
Eval mínimo do Golden Dataset — GymSite Intelligence.

Uso:
  python eval/run_eval.py
  python eval/run_eval.py --case fortaleza_parangaba_20260528
  python eval/run_eval.py --with-positioning   # nightly / manual (LLM)
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
from eval.evaluators.positioning_quality_eval import evaluate_positioning_quality


def _load_case(case_dir: Path) -> tuple[dict, dict, dict[str, Any]]:
    golden = json.loads((case_dir / "expected_output.json").read_text(encoding="utf-8"))
    report = json.loads((case_dir / "full_report.json").read_text(encoding="utf-8"))
    supplement: dict[str, Any] = {}
    for name in ("cno_cruzamento_cnpj.json", "cno_live.json"):
        path = case_dir / name
        if path.is_file():
            supplement[name] = json.loads(path.read_text(encoding="utf-8"))
    return golden, report, supplement


def run_case(case_dir: Path, *, with_positioning: bool) -> dict:
    golden, report, supplement = _load_case(case_dir)
    cno = evaluate_cno_consistency(report, golden, supplement=supplement or None)
    out: dict[str, Any] = {
        "case_id": golden.get("case_id", case_dir.name),
        "approved": golden.get("approved", False),
        "cno": {
            "status": cno.status,
            "reason": cno.reason,
            "issues": cno.issues,
        },
    }
    if with_positioning:
        pos = evaluate_positioning_quality(report, golden)
        out["positioning"] = {
            "status": pos.status,
            "reason": pos.reason,
            "issues": pos.issues,
        }
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Golden dataset eval")
    parser.add_argument("--dataset", default="eval/golden_dataset")
    parser.add_argument("--case", help="case_id ou nome de pasta")
    parser.add_argument(
        "--with-positioning",
        action="store_true",
        help="Inclui PositioningQualityEval (LLM; requer GOOGLE_API_KEY)",
    )
    args = parser.parse_args()

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
    cno_failed = 0
    pos_failed = 0

    for d in dirs:
        if not d.exists():
            print(f"SKIP {args.case}: pasta não encontrada")
            return 1
        r = run_case(d, with_positioning=args.with_positioning)
        results.append(r)
        cno_icon = icons.get(r["cno"]["status"], "?")
        line = f"[{cno_icon}] {r['case_id']} — CNO {r['cno']['status']}"
        if args.with_positioning:
            pos_st = r["positioning"]["status"]
            pos_icon = icons.get(pos_st, "?")
            line += f" | POS {pos_icon} {pos_st}"
        print(line)
        for issue in r["cno"]["issues"]:
            print(f"      • CNO {issue.get('field')}: {issue.get('message')}")
        if args.with_positioning and r["positioning"]["issues"]:
            for issue in r["positioning"]["issues"]:
                print(f"      • POS {issue.get('message')}")
        if r["cno"]["status"] == "FAIL":
            cno_failed += 1
        if args.with_positioning and r["positioning"]["status"] == "FAIL":
            pos_failed += 1

    summary = f"\n{len(results)} casos | CNO FAIL: {cno_failed}"
    if args.with_positioning:
        summary += f" | POS FAIL: {pos_failed}"
    print(summary)

    if cno_failed:
        return 1
    if args.with_positioning and pos_failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
