# agents/a2_demo_analyst.py
"""
A2 — DemoAnalyst — agente DETERMINÍSTICO (sem LLM).

REFATOR custo-LLM (2026-06-16):
Antes era um LlmAgent (gemini-3.6-flash) que chamava a macro determinística
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
import os
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


def _num_campo(v) -> float:
    """Coage valor de campo demográfico que às vezes vem dict {valor/renda_media:..}
    (não só número/str) — senão float()/int() levantava TypeError e derrubava o A2."""
    if isinstance(v, dict):
        for k in ("valor", "renda_media", "value", "media"):
            if v.get(k) is not None:
                v = v[k]
                break
        else:
            return 0.0
    try:
        return float(str(v).replace(",", ".")) if v not in (None, "") else 0.0
    except (TypeError, ValueError):
        return 0.0


def _insights_deterministicos(r: dict) -> list[str]:
    """Os 3 insights que o LLM 'escrevia' — eram templates derivados dos números.
    Recriados em Python (determinísticos, auditáveis, zero token)."""
    pub = int(_num_campo(r.get("publico_potencial_fitness")))
    renda = _num_campo(r.get("renda_bairro") if r.get("renda_bairro") is not None
                       else (r.get("renda_media_per_capita") or r.get("renda_media_domiciliar")))
    score = _num_campo(r.get("score_demografico"))
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
                insights = _insights_deterministicos(r)
                # Gancho mkt: perfil sexo×idade do público fitness (município, Censo 2022/BQ)
                try:
                    from tools.perfil_sexo_idade_tools import (
                        insight_gancho_mkt,
                        perfil_sexo_publico_fitness,
                    )

                    perfil = await asyncio.to_thread(
                        perfil_sexo_publico_fitness, r.get("codigo_ibge")
                    )
                    if perfil:
                        r = {**r, "perfil_sexo_publico": perfil}
                        linha = insight_gancho_mkt(perfil)
                        if linha:
                            insights = insights + [linha]
                except Exception as e:
                    print(f"[A2 gancho sexo×idade] falha (degrada): {type(e).__name__}: {e}")
                # Cross-query de SETOR (#5 Apontamento 1, forma prod-viável): densidade
                # populacional no raio do bairro via espelho censo_setor (não BQ-runtime,
                # que falha em prod). Flag A2_FONTE: 'espelho' (default) liga, 'rest' pula.
                # Enriquece só (renda/faixa seguem das fontes atuais); degrada limpo.
                if os.getenv("A2_FONTE", "espelho").strip().lower() != "rest":
                    try:
                        from tools.censo_setor_tools import demografia_setor_censo
                        from tools.nominatim_geocoder import nominatim_geocode

                        _lat = r.get("latitude") or r.get("lat")
                        _lng = r.get("longitude") or r.get("lng")
                        if _lat is None or _lng is None:
                            _g = await asyncio.to_thread(
                                nominatim_geocode, f"{bairro}, {cidade}, {uf}, Brasil"
                            )
                            if _g:
                                _lat, _lng = _g["lat"], _g["lon"]
                        if _lat is not None and _lng is not None:
                            setor = await asyncio.to_thread(
                                lambda la, lo, idm: demografia_setor_censo(
                                    la, lo, id_municipio=idm),
                                float(_lat), float(_lng),
                                str(r.get("codigo_ibge") or "") or None,
                            )
                            if isinstance(setor, dict) and setor.get("populacao"):
                                r = {**r, "densidade_setor": setor}
                    except Exception as e:
                        print(f"[A2 densidade setor] falha (degrada): {type(e).__name__}: {e}")
                r = {**r, "insights": insights}
        except Exception as e:  # nunca derruba o pipeline — A6 degrada com score None
            print(f"[A2 determinístico] falha: {type(e).__name__}: {e}")
            r = {"erro": f"{type(e).__name__}: {e}", "score_demografico": None}

        # C6.2: valida o contrato de saída (leniente — loga divergência, não rejeita).
        try:
            from models.pipeline_schemas import AnaliseDemografica, validar_lenient

            r = validar_lenient(AnaliseDemografica, r, agente="A2")
        except Exception:
            pass

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
