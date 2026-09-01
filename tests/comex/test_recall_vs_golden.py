"""Recall scoring vs golden importadores (Company Intel lite success metric)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.company_intel_recall import normalize_importer_name, recall_at_k  # noqa: E402

ROLLUP = ROOT / "docs" / "comex" / "golden" / "importadores_9506_rollup.json"


@pytest.fixture
def golden_names() -> list[str]:
    rows = json.loads(ROLLUP.read_text(encoding="utf-8"))
    return [r["importador"] for r in rows]


def test_normalize_stable() -> None:
    a = normalize_importer_name("LIFE FITNESS COMERCIO DE EQUIPAMENTOS DO BRASIL LTDA.")
    b = normalize_importer_name("Life Fitness Comércio de Equipamentos do Brasil Ltda")
    assert a == b
    assert "LIFE FITNESS" in a


def test_perfect_recall_when_candidates_contain_all(golden_names: list[str]) -> None:
    # simulate "we found everyone" — success ceiling for L2/L3
    scored = recall_at_k(golden_names, golden_names, k=50)
    assert scored["recall"] == 1.0
    assert scored["misses"] == []


def test_partial_recall_example(golden_names: list[str]) -> None:
    # first cut: only the top-3 TEU names "discovered"
    partial = [
        "STONE IMPORTACAO, COMERCIO ATACADISTA LTDA",
        "AC COMERCIAL IMPORTADORA E EXPORTADORA LTDA",
        "FIRST S A",
        "EMPRESA ALEATORIA XYZ LTDA",
    ]
    scored = recall_at_k(golden_names, partial, k=50)
    assert scored["n_golden"] == 12
    assert scored["recall"] == pytest.approx(3 / 12)
    assert len(scored["hits"]) == 3
    assert len(scored["misses"]) == 9


def test_empty_candidates_zero_recall(golden_names: list[str]) -> None:
    scored = recall_at_k(golden_names, [], k=50)
    assert scored["recall"] == 0.0
    assert len(scored["misses"]) == 12
