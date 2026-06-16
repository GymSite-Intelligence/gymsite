# agents/a5_contact_hunter.py
"""
A5 — ContactHunter — agente DETERMINÍSTICO (sem LLM).

REFATOR custo-LLM (2026-06-16):
Antes era um LlmAgent (gemini-2.5-flash) "redator puro" que chamava a macro
determinística `gerar_contato_decisor_completo` e ecoava o JSON via output_key.
A macro já monta TUDO (decisor, canal, script_abordagem, próximos passos); o LLM
só re-emitia. Telemetria: ~225k tokens de INPUT por relatório pra produzir ~786
de output (6,6% do custo) sem decisão própria. Já havia um after_agent_callback
de fallback que repopulava da macro quando o LLM vinha vazio — sinal de que o LLM
era dispensável. Agora é um BaseAgent que roda a macro direto e grava
`contato_decisor` no state. Zero token LLM, mesmo resultado. Padrão do A3a/A2.
"""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

from tools.contact_tools import gerar_contato_decisor_completo


class _StateShim:
    """tool_context mínimo — a macro de contato só lê `.state`."""

    __slots__ = ("state",)

    def __init__(self, state):
        self.state = state


class ContactHunterAgent(BaseAgent):
    """A5 determinístico: roda a macro de contato e grava contato_decisor no state."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        try:
            result = await asyncio.to_thread(
                gerar_contato_decisor_completo, _StateShim(state)
            )
            if not isinstance(result, dict):
                result = {}
        except Exception as e:  # nunca derruba o pipeline — A6 degrada sem contato
            print(f"[A5 determinístico] falha: {type(e).__name__}: {e}")
            result = {"erro": f"{type(e).__name__}: {e}"}

        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            actions=EventActions(state_delta={"contato_decisor": result}),
        )


contact_hunter_agent = ContactHunterAgent(
    name="ContactHunter",
    description=(
        "A5 determinístico (sem LLM): identifica decisor do candidato #1 + gera "
        "script de abordagem via macro-tool Python. Grava contato_decisor no state. "
        "Substitui o agente-eco LLM (~225k tokens/run só pra formatar a macro)."
    ),
)
