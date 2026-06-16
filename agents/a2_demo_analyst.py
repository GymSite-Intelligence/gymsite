# agents/a2_demo_analyst.py
"""
A2 — DemoAnalyst — agente DETERMINÍSTICO (sem LLM).

REFATOR custo-LLM (2026-06-16):
Antes era um LlmAgent (gemini-2.5-flash) que chamava a macro determinística
`analise_demografica_completa` e ECOAVA o JSON via output_key + preenchia
`insights[]`/`recomendacao` — templates 100% deriváveis dos números da tool.
A telemetria mostrou ~135k tokens de INPUT por relatório só pra isso, e os
`insights`/`recomendacao` NÃO são consumidos por ninguém (A6 lê só
`score_demografico`; o PDF lê `insights_estrategicos` do A0). Agora é um
BaseAgent que roda a macro direto e grava `analise_demografica` no state.
Mesmo resultado downstream, zero token de LLM. Mesmo padrão do A3a.

NOTA (dívida separada): o score demográfico ainda usa renda do bairro via CKAN
2010 (`enrich_demografia_bairro`) — mesma fonte legada do bug do A4 (ver
fix a4-renda-2022). Migrar p/ IBGE 2022 é fix à parte (muda score_demografico).
"""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

from tools.competitor_tools import _parse_market_context
from tools.ibge_tools import analise_demografica_completa
from tools.parametros_metodologia import param


def _loc_do_state(state) -> tuple[str, str, str | None]:
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
    return cidade, uf, (bairro or None)


def _insights_deterministicos(r: dict) -> list[str]:
    """Os 3 insights que o LLM 'escrevia' — eram templates derivados dos números.
    Recriados em Python (determinísticos, auditáveis, zero token)."""
    pub = int(r.get("publico_potencial_fitness") or 0)
    renda = float(r.get("renda_bairro") or r.get("renda_media_domiciliar") or 0)
    score = float(r.get("score_demografico") or 0)
    classe = str(r.get("classificacao") or "—")
    out: list[str] = []
    if pub:
        out.append(f"Potencial de captação: ~{pub:,} alunos potenciais na faixa fitness.".replace(",", "."))
    if renda:
        suporta = "suporta" if renda >= param("score_demo_renda_baixa") else "não suporta"
        out.append(f"Renda de R$ {renda:,.0f} {suporta} mensalidade premium.".replace(",", "."))
    if score:
        out.append(f"Score {score:.1f}/10 indica mercado {classe.lower()}.")
    return out


class DemoAnalystAgent(BaseAgent):
    """A2 determinístico: roda a macro IBGE e grava analise_demografica no state."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        cidade, uf, bairro = _loc_do_state(state)
        try:
            r = await asyncio.to_thread(
                analise_demografica_completa, cidade, uf, "18-45", bairro
            )
            if isinstance(r, dict):
                r = {**r, "insights": _insights_deterministicos(r)}
        except Exception as e:  # nunca derruba o pipeline — A6 degrada com score None
            print(f"[A2 determinístico] falha: {type(e).__name__}: {e}")
            r = {"erro": f"{type(e).__name__}: {e}", "score_demografico": None}

        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            actions=EventActions(state_delta={"analise_demografica": r}),
        )


demo_analyst_agent = DemoAnalystAgent(
    name="DemoAnalyst",
    description=(
        "A2 determinístico (sem LLM): análise demográfica IBGE Censo 2022 em 1 passo "
        "Python (pop/faixa/renda/score). Grava analise_demografica no state. Substitui "
        "o agente-eco LLM (~135k tokens/run gerando insights não-consumidos)."
    ),
)
