"""A1 GeoScout — listings filtrados + aluguel MRLR.

Antes: BaseAgent rodava `analisar_pontos_comerciais_completo` (SearchAPI âncoras
supermercado/concessionária + área por tipo). Evidência Pirapora-MG Centro
(2026-08-05): ≥90% `indireto-heuristico`, área 600 repetida, contaminação
Diadema-SP. Output não é ponto decidível.

Agora: busca anúncios individuais via SearchAPI, filtra geografia/área e anexa
aluguel MRLR. Lista vazia permanece vazia e explícita.
"""
from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

from tools.competitor_tools import _parse_market_context
from tools.a1_listing_pipeline import buscar_candidatos_listing_mrlr


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


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


class GeoScoutAgent(BaseAgent):
    """A1 determinístico: listing SearchAPI filtrado + MRLR."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        cidade, uf, bairro = _loc_do_state(state)
        raw_params = state.get("input_params")
        params: dict = raw_params if isinstance(raw_params, dict) else {}
        area_min = _positive_int(params.get("area_m2_min"), 500)
        area_max = _positive_int(params.get("area_m2_max"), 5000)
        try:
            result = await asyncio.to_thread(
                buscar_candidatos_listing_mrlr,
                cidade=cidade,
                uf=uf,
                bairro=bairro,
                area_m2_min=area_min,
                area_m2_max=area_max,
            )
            r = result if isinstance(result, dict) else {
                "status": "ok_vazio",
                "total_candidatos": 0,
                "candidatos": [],
                "aviso": "Busca de listings retornou formato inválido.",
            }
        except Exception as exc:
            r = {
                "status": "ok_vazio",
                "total_candidatos": 0,
                "candidatos": [],
                "aviso": f"Listings indisponíveis: {type(exc).__name__}: {exc}",
                "fonte": "listing_cascata_searchapi+mrlr",
                "cidade": cidade,
                "uf": uf,
                "bairro": bairro,
            }
        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            actions=EventActions(state_delta={
                "candidatos_geoscout_pronto": r,
                "candidatos_geoscout": r,
            }),
        )


geoscout_agent = GeoScoutAgent(
    name="GeoScout",
    description=(
        "A1 determinístico: encontra anúncios individuais no bairro via SearchAPI, "
        "filtra geografia e área, e anexa aluguel MRLR."
    ),
)
