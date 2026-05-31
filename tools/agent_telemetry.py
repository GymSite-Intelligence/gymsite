"""
OpenTelemetry spans para agentes Google ADK (A0–A9).

Injeta via before_agent_callback / after_agent_callback no _attach_telemetry()
de gymsite_intelligence/agent.py.

Política LGPD: nunca gravar state bruto no span — apenas atributos escalares
sanitizados via tools.sanitize.sanitize_state.
"""
from __future__ import annotations

from opentelemetry import trace

from tools.sanitize import sanitize_state

# Mapeia id(callback_context) → Span ativo.
# before_agent_callback e after_agent_callback são sempre chamados em par
# pelo Runner do ADK, mesmo em caso de exceção.
_agent_spans: dict[int, trace.Span] = {}

# Chaves do state ADK permitidas nos spans (valores já sanitizados).
_SPAN_STATE_ATTRS: dict[str, str] = {
    "cnpj": "cnpj_masked",
    "email": "email_masked",
    "telefone": "phone_masked",
    "whatsapp": "phone_masked",
    "endereco": "endereco_masked",
    "endereco_cnpj": "endereco_masked",
    "cidade": "cidade",
    "uf": "uf",
    "municipio": "municipio",
    "bairro": "bairro",
}


def _apply_sanitized_state_to_span(span: trace.Span, state: dict) -> None:
    """Grava no span apenas campos whitelisted e já mascarados."""
    span.set_attribute("state.keys_count", len(state))
    safe = sanitize_state(state)

    for src_key, attr_name in _SPAN_STATE_ATTRS.items():
        val = safe.get(src_key)
        if val is not None and val != "":
            span.set_attribute(attr_name, str(val)[:256])

    contato = safe.get("contato_cnpj")
    if isinstance(contato, dict):
        if contato.get("email"):
            span.set_attribute("contato.email_masked", str(contato["email"])[:256])
        phone = contato.get("whatsapp") or contato.get("telefone")
        if phone:
            span.set_attribute("contato.phone_masked", str(phone)[:256])


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
        if isinstance(state, dict):
            _apply_sanitized_state_to_span(span, state)
    except Exception:
        pass
    span.end()
