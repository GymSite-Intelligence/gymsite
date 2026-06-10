"""Pytest do E2E gate (sem API ADK completa)."""
from __future__ import annotations

import pytest

from scripts.batch.e2e_gate import (
    check_a1_ckan,
    check_a2_cvm,
    check_a3_benchmarks,
    check_a4_bundle,
    check_a4_dr_skip,
    check_a5_integration,
    run_e2e_for_stage,
)


@pytest.mark.e2e
def test_e2e_a1():
    assert check_a1_ckan() == 0


@pytest.mark.e2e
def test_e2e_a3():
    assert check_a3_benchmarks() == 0


@pytest.mark.e2e
def test_e2e_dr_skip():
    assert check_a4_bundle(rebuild=False) == 0
    assert check_a4_dr_skip() == 0


@pytest.mark.e2e
def test_e2e_stage_all():
    assert run_e2e_for_stage("a6_e2e") == 0
