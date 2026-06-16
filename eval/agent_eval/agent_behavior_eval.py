"""Evaluator comportamental do agente isca (GymSite).

Deterministico: aplica asserts de keyword/regex sobre a resposta do agente.
Retorna EvalResult (eval/evaluators/base.py) para integrar ao padrao do repo.

Tipos de assert suportados (em cases/*.json, chave "assert"):
  must_contain_any   : lista — passa se a resposta contem PELO MENOS um.
  must_contain_all   : lista — passa se contem TODOS.
  must_not_contain_any : lista — FAIL se contem QUALQUER um (ex.: fontes sigilosas).
  regex_any          : lista de regex — passa se PELO MENOS um casa.
  regex_none         : lista de regex — FAIL se QUALQUER um casa.
  gate               : "PR" | "nightly" (informativo; usado pelo runner).

Match case-insensitive e tolerante a acentos.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

try:
    from eval.evaluators.base import EvalResult
except Exception:  # execucao standalone
    from dataclasses import dataclass, field

    @dataclass
    class EvalResult:  # type: ignore
        status: str
        evaluator: str = ""
        reason: str = ""
        issues: list = field(default_factory=list)

        @property
        def passed(self) -> bool:
            return self.status in ("PASS", "SKIP")


EVALUATOR_NAME = "agent_behavior"


def _norm(text: str) -> str:
    """lowercase + remove acentos para match robusto."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower()


def _contains(haystack: str, needle: str) -> bool:
    return _norm(needle) in haystack


def evaluate(case: dict[str, Any], response: str) -> EvalResult:
    """Aplica os asserts do caso sobre a resposta do agente."""
    spec = case.get("assert", {})
    case_id = case.get("case_id", "?")
    if not response or not response.strip():
        return EvalResult("SKIP", EVALUATOR_NAME, f"{case_id}: sem resposta (transcript vazio)")

    hay = _norm(response)
    issues: list[dict[str, Any]] = []

    any_terms = spec.get("must_contain_any") or []
    if any_terms and not any(_contains(hay, t) for t in any_terms):
        issues.append({"rule": "must_contain_any", "expected_one_of": any_terms})

    for t in spec.get("must_contain_all") or []:
        if not _contains(hay, t):
            issues.append({"rule": "must_contain_all", "missing": t})

    for t in spec.get("must_not_contain_any") or []:
        if _contains(hay, t):
            issues.append({"rule": "must_not_contain_any", "forbidden": t})

    rx_any = spec.get("regex_any") or []
    if rx_any and not any(re.search(p, response, re.I) for p in rx_any):
        issues.append({"rule": "regex_any", "expected_one_of": rx_any})

    for p in spec.get("regex_none") or []:
        if re.search(p, response, re.I):
            issues.append({"rule": "regex_none", "forbidden_match": p})

    if not issues:
        return EvalResult("PASS", EVALUATOR_NAME, f"{case_id}: ok")

    # Violacao de sigilo/LGPD/seguranca = FAIL forte; demais = FAIL padrao.
    hard = {"must_not_contain_any", "regex_none"}
    status = "FAIL" if any(i["rule"] in hard for i in issues) else "FAIL"
    return EvalResult(status, EVALUATOR_NAME, f"{case_id}: {len(issues)} violacao(oes)", issues)
