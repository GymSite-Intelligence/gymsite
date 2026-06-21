"""Gate de recência da dor (≤6 meses) — `_review_recente_6m`.

Regra de produto: dor pra insight de posicionamento só vale se RECENTE. Dor de >6 meses
é stale (a academia pode já ter consertado). Antes o gate era 1 ano (`_review_recente_1ano`)
— deixava entrar dor de 8-11 meses. Agora ≤6m, PT+EN. Pura, offline.
"""
import pytest

from tools.competitor_tools import _review_recente_6m as recente


@pytest.mark.parametrize("data_rel, esperado", [
    ("2 months ago", True),
    ("6 months ago", True),      # limite inclusivo
    ("7 months ago", False),     # > 6 → fora (antes entrava)
    ("8 months ago", False),
    ("11 months ago", False),
    ("a month ago", True),       # 1 mês
    ("a year ago", False),
    ("2 years ago", False),
    ("há 3 meses", True),
    ("há 7 meses", False),       # PT, > 6
    ("há 1 mês", True),
    ("há 1 ano", False),
    ("2 weeks ago", True),
    ("yesterday", True),
    ("3 days ago", True),
    ("", True),                  # sem label = mantém (defensivo)
    (None, True),
])
def test_gate_6_meses(data_rel, esperado):
    assert recente(data_rel) is esperado


def test_janela_configuravel():
    # cap explícito ainda funciona (ex: 3 meses)
    assert recente("4 months ago", meses=3) is False
    assert recente("2 months ago", meses=3) is True
