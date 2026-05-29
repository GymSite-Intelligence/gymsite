#!/usr/bin/env python3
"""Testes leves do módulo kimi_research (sem OpenClaw obrigatório)."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))


def test_queries_count():
    from tools.kimi_research import _queries_paralelas

    qs = _queries_paralelas("Fortaleza", "Meireles", "academia", "25-40")
    assert len(qs) == 5
    assert qs[0][0] == "demografia"


def test_kimi_provider_flag():
    import os
    from tools.kimi_research import kimi_provider_ativo

    os.environ.pop("A0_RESEARCH_PROVIDER", None)
    assert kimi_provider_ativo() is False
    os.environ["A0_RESEARCH_PROVIDER"] = "kimi"
    assert kimi_provider_ativo() is True
    os.environ.pop("A0_RESEARCH_PROVIDER", None)


if __name__ == "__main__":
    test_queries_count()
    test_kimi_provider_flag()
    print("ok")
