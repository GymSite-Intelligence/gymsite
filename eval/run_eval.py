#!/usr/bin/env python3
"""
Eval mínimo do Golden Dataset — GymSite Intelligence.

Uso:
  python eval/run_eval.py
  python eval/run_eval.py --case fortaleza_parangaba_20260528
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


def _load_case(case_dir: Path) -> tuple[dict, dict, dict[str, Any]]:
    golden = json.loads((case_dir / "expected_output.json").read_text(encoding="utf-8"))
    report = json.loads((case_dir / "full_report.json").read_text(encoding="utf-8"))
    supplement: dict[str, Any] = {}
    for name in ("cno_cruzamento_cnpj.json", "cno_live.json"):
        path = case_dir / name
        if path.is_file():
            supplement[name] = json.loads(path.read_text(encoding="utf-8"))
    return golden, report, supplement


def run_case(case_dir: Path) -> dict:
    golden, report, supplement = _load_case(case_dir)
    cno = evaluate_cno_consistency(report, golden, supplement=supplement or None)
    return {
        "case_id": golden.get("case_id", case_dir.name),
        "approved": golden.get("approved", False),
        "cno": {
            "status": cno.status,
            "reason": cno.reason,
            "issues": cno.issues,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Golden dataset eval")
    parser.add_argument("--dataset", default="eval/golden_dataset")
    parser.add_argument("--case", help="case_id ou nome de pasta")
    args = parser.parse_args()

    dataset = ROOT / args.dataset
    if args.case:
        dirs = [dataset / args.case]
    else:
        dirs = sorted(p for p in dataset.iterdir() if p.is_dir() and (p / "expected_output.json").is_file())

    results = []
    failed = 0
    for d in dirs:
        if not d.exists():
            print(f"SKIP {args.case}: pasta não encontrada")
            return 1
        r = run_case(d)
        results.append(r)
        icon = {"PASS": "OK", "WARN": "!!", "FAIL": "XX", "SKIP": "--"}.get(r["cno"]["status"], "?")
        print(f"[{icon}] {r['case_id']} — CNO {r['cno']['status']}")
        for issue in r["cno"]["issues"]:
            print(f"      • {issue.get('field')}: {issue.get('message')}")
        if r["cno"]["status"] == "FAIL":
            failed += 1

    print(f"\n{len(results)} casos | CNO FAIL: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
