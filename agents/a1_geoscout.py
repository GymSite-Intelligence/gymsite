# agents/a1_geoscout.py
"""A1 GeoScout — DETERMINÍSTICO (sem LLM).

Antes era LlmAgent com thinking=0 que SÓ copiava o JSON da macro
`analisar_pontos_comerciais_completo` (100% determinística) pro output_key. Era
passthrough caro + risco de truncar o array de candidatos (incidente b5b0e627:
14 candidatos → 0 no A6 porque o LLM truncou ao copiar).

Vira BaseAgent (igual A2/A3a): roda a macro direto e grava o resultado. Elimina:
- variância (mesma praça = mesmo resultado)
- custo LLM (uma chamada Gemini Flash a menos por run)
- a truncagem do array (o LLM não toca mais o JSON)
- exposição ao dunning/Vertex (A1 sobrevive mesmo com billing travado)

Mapa de determinização VEC: "o LLM raciocina sobre dado, não PRODUZ dado". A1 só
produzia (copiava) → determinizado.
"""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

from tools.anchoring_tools import analisar_pontos_comerciais_completo
from tools.competitor_tools import _parse_market_context


def _loc_do_state(state) -> tuple[str, str, str]:
    """cidade/uf/bairro do input_params (api.py) + market_context (A0)."""
    ip = state.get("input_params") if isinstance(state.get("input_params"), dict) else {}
    cidade = (state.get("cidade") or ip.get("cidade") or "").strip()
    uf = (state.get("uf") or ip.get("uf") or "").strip()
    bairro = (state.get("bairro") or ip.get("bairro") or "").strip()
    ctx = _parse_market_context(state.get("market_context"))
    if isinstance(ctx, dict):
        inner = ctx.get("market_context") if isinstance(ctx.get("market_context"), dict) else ctx
        if isinstance(inner, dict):
            cidade = cidade or (inner.get("cidade") or "").strip()
            uf = uf or (inner.get("uf") or "").strip()
            bairro = bairro or (inner.get("bairro") or "").strip()
    return cidade, uf, bairro


class GeoScoutAgent(BaseAgent):
    """A1 determinístico: roda a macro de pontos comerciais e grava o resultado."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        cidade, uf, bairro = _loc_do_state(state)
        try:
            # macro é síncrona — roda em thread pra não travar o loop
            r = await asyncio.to_thread(
                analisar_pontos_comerciais_completo, bairro, cidade, uf
            )
            if not isinstance(r, dict):
                r = {"erro": "macro retornou não-dict", "total_candidatos": 0, "candidatos": []}
        except Exception as e:  # nunca derruba o pipeline
            r = {"erro": f"{type(e).__name__}: {e}", "total_candidatos": 0, "candidatos": []}

        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            # candidatos_geoscout_pronto = snapshot que o A6 lê PRIMEIRO (bypassa o LLM,
            # como o _persistir_macro_no_state fazia). candidatos_geoscout = output_key
            # legado p/ consumidores que leem essa chave.
            actions=EventActions(state_delta={
                "candidatos_geoscout_pronto": r,
                "candidatos_geoscout": r,
            }),
        )


geoscout_agent = GeoScoutAgent(
    name="GeoScout",
    description=(
        "A1 determinístico (sem LLM): identifica zonas comerciais-âncora p/ academias "
        "via macro Google Maps (geocode + nearby + text + score + polos + listings). "
        "Retorna endereços-âncora para field research, não imóveis vagos."
    ),
)
