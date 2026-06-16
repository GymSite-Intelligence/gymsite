# agents/a3a_competitor_search.py
"""
A3a — CompetitorSearch (busca + enrichment) — agente DETERMINÍSTICO (sem LLM).

Sub-agente da fase competitiva. Busca academias concorrentes, processa reviews
e faz enrichment. NÃO faz análise agregada — isso é do A3b.

REFATOR custo-LLM (2026-06-14):
Antes era um LlmAgent (gemini-2.5-flash) cujo único trabalho era chamar a macro
determinística `analisar_concorrentes_a3a_completo` e ECOAR o JSON de volta via
output_key. O LLM não decidia nada: re-enviava o state inteiro (~83k tokens por
relatório, medido em metrics/tokens_pipeline.csv) só pra repetir o resultado da
tool. Agora é um BaseAgent que roda a macro direto e grava `concorrentes_brutos`
no state via state_delta. Mesmo resultado, zero token de LLM.

REFATOR Task #48 (2026-05-09):
A macro `analisar_concorrentes_a3a_completo` consolidou 4 tools em 1 (busca +
reconciliação A0 + reviews + enrichment + classificação de dores via Gemini batch).
O pipeline antigo ocupava 9 round-trips do LLM (~244k tokens).
"""
from __future__ import annotations

from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

from tools.competitor_tools import (
    analisar_concorrentes_a3a_completo,
    _parse_market_context,
)

_ERRO_VAZIO = {
    "concorrentes_brutos": [],
    "concorrentes_excluidos": [],
    "redes_a0_solicitadas": [],
    "redes_a0_cobertas": [],
    "redes_a0_nao_encontradas": [],
}


class _StateShim:
    """tool_context mínimo — as tools de concorrência só leem `.state`."""

    __slots__ = ("state",)

    def __init__(self, state):
        self.state = state


def _extrair_bairro_cidade(state) -> tuple[str, str]:
    """bairro/cidade do market_context (output do A0), com fallback de topo do state."""
    bairro = (state.get("bairro") or "").strip()
    cidade = (state.get("cidade") or "").strip()
    ctx = _parse_market_context(state.get("market_context"))
    if isinstance(ctx, dict):
        inner = ctx.get("market_context")
        inner = inner if isinstance(inner, dict) else ctx
        bairro = bairro or (inner.get("bairro") or "").strip()
        cidade = cidade or (inner.get("cidade") or "").strip()
    return bairro, cidade


class CompetitorSearchAgent(BaseAgent):
    """A3a determinístico: roda a macro de busca+enrichment e grava no state."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        bairro, cidade = _extrair_bairro_cidade(state)
        try:
            resultado = await analisar_concorrentes_a3a_completo(
                _StateShim(state), bairro, cidade
            )
        except Exception as e:  # nunca derruba o pipeline — A3b lida com lista vazia
            print(f"[A3a determinístico] falha: {type(e).__name__}: {e}")
            resultado = {"erro": f"{type(e).__name__}: {e}", **_ERRO_VAZIO}

        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            actions=EventActions(state_delta={"concorrentes_brutos": resultado}),
        )


competitor_search_agent = CompetitorSearchAgent(
    name="CompetitorSearch",
    description=(
        "A3a determinístico (sem LLM): busca + reconciliação A0 + reviews + "
        "enrichment + classificação de dores em 1 passo Python. Grava "
        "concorrentes_brutos no state pra A3b. Substitui o agente-eco LLM (~83k tokens)."
    ),
)
