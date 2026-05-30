"""
OpenTelemetry spans para agentes Google ADK (A0–A6).

Injeta via before_agent_callback / after_agent_callback no _attach_telemetry()
de gymsite_intelligence/agent.py.
"""
from __future__ import annotations

from opentelemetry import trace

from tools.sanitize import mask_cnpj, mask_phone, mask_email

# Mapeia id(callback_context) → Span ativo.
# before_agent_callback e after_agent_callback são sempre chamados em par
# pelo Runner do ADK, mesmo em caso de exceção.
_agent_spans: dict[int, trace.Span] = {}


def before_agent_callback(callback_context) -> None:
    """Starta span quando o agente começa a rodar."""
    tracer = trace.get_tracer("gymsite.adk")
    agent_name = getattr(callback_context, "agent_name", "unknown")
    span = tracer.start_span(f"agent.{agent_name}")
    span.set_attribute("agent.name", agent_name)
    _agent_spans[id(callback_context)] = span


def after_agent_callback(callback_context) -> None:
    """Finaliza span quando o agente termina."""
    span = _agent_spans.pop(id(callback_context), None)
    if span is None:
        return
    try:
        state = getattr(callback_context, "state", None) or {}
        # Guarda contagem de keys no state como métrica leve (sem valores)
        span.set_attribute("state.keys_count", len(state))
        # Sanitiza CNPJ se presente no state
        cnpj = state.get("cnpj")
        if cnpj:
            span.set_attribute("cnpj_masked", mask_cnpj(cnpj) or "redacted")
    except Exception:
        pass
    span.end()
