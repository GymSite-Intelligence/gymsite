"""Runner do eval comportamental do agente isca (GymSite).

Modos:
  --transcript  (default): le respostas ja coladas do Preview em
                 eval/agent_eval/responses/<case_id>.txt e aplica os asserts.
                 100% offline e reproduzivel, sem credencial.
  --live        : STUB. Desativado por padrao. Requer endpoint/credencial do
                 agente, configurado manualmente pelo responsavel. NAO cria
                 chaves nem faz deploy.

Uso:
  python eval/agent_eval/run_agent_eval.py
  python eval/agent_eval/run_agent_eval.py --case sigilo_fontes
  python eval/agent_eval/run_agent_eval.py --gate PR

Exit code: 0 se nenhum FAIL nos casos do gate selecionado; 1 caso contrario.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES_DIR = HERE / "cases"
RESPONSES_DIR = HERE / "responses"

sys.path.insert(0, str(HERE.parent.parent))  # raiz do repo no path
from eval.agent_eval.agent_behavior_eval import evaluate  # noqa: E402

ICON = {"PASS": "[OK]", "WARN": "[!!]", "FAIL": "[XX]", "SKIP": "[--]"}


def load_cases(case_filter: str | None, gate: str | None) -> list[dict]:
    cases = []
    for path in sorted(CASES_DIR.glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        if case_filter and case.get("case_id") != case_filter:
            continue
        if gate and (case.get("assert", {}).get("gate") != gate):
            continue
        cases.append(case)
    return cases


def load_response(case_id: str) -> str:
    path = RESPONSES_DIR / f"{case_id}.txt"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def run_transcript(cases: list[dict]) -> int:
    fails = 0
    for case in cases:
        cid = case.get("case_id", "?")
        resp = load_response(cid)
        result = evaluate(case, resp)
        print(f"{ICON.get(result.status, result.status)} {cid} — {result.reason}")
        for issue in result.issues:
            print(f"      - {issue}")
        if result.status == "FAIL":
            fails += 1
    print(f"\n{len(cases)} caso(s) | FAIL: {fails}")
    return 1 if fails else 0


def run_live(cases: list[dict]) -> int:
    raise SystemExit(
        "modo --live nao configurado. Defina endpoint/credencial do agente e "
        "implemente call_agent(user_message). Por seguranca, este runner nao "
        "cria chaves nem faz deploy. Use --transcript."
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Eval comportamental do agente isca")
    ap.add_argument("--transcript", action="store_true", help="modo offline (default)")
    ap.add_argument("--live", action="store_true", help="stub desativado")
    ap.add_argument("--case", help="rodar apenas um case_id")
    ap.add_argument("--gate", choices=["PR", "nightly"], help="filtrar por gate")
    args = ap.parse_args()

    cases = load_cases(args.case, args.gate)
    if not cases:
        print("nenhum caso encontrado (verifique cases/ e filtros).")
        return 0

    if args.live:
        return run_live(cases)
    return run_transcript(cases)


if __name__ == "__main__":
    raise SystemExit(main())
