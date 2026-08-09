"""Self-transfer ADK (NVIDIA) → parse + pinado."""
from __future__ import annotations

from agents_site.runner import _nome_self_transfer, _pinado_por_nome_adk, _resolver_agente


def test_parse_self_transfer_error():
    exc = ValueError("Agent 'Mercado' cannot transfer to itself.")
    assert _nome_self_transfer(exc) == "Mercado"
    assert _nome_self_transfer(RuntimeError("outra coisa")) is None


def test_pinado_mercado_por_nome():
    pin = _pinado_por_nome_adk("Mercado")
    assert pin is not None
    assert pin.name == "Mercado"
    assert pin is _resolver_agente("mercado")
