# agents/a4_financial_estimator.py
"""A4 — FinancialEstimator DETERMINÍSTICO (BaseAgent, sem LLM).

Antes era LlmAgent que copiava a macro `analise_financeira_a4_completo` (100%
determinística — score/modelo/cenários/alertas) e só redigia 1 campo: `justificativa`.
Os números já eram snapshot (analise_financeira_pronto, A6 lê direto). O LLM era
passthrough + 1 frase — e às vezes alucinava (run_code, dropava campos).

Vira BaseAgent (igual A1/A2): roda a macro + monta a `justificativa` por TEMPLATE
determinístico (modelo + margem + payback + gênero). Elimina variância, custo (Flash
a menos/run) e a exposição ao dunning. Mapa de determinização: LLM não PRODUZ dado.
"""
from __future__ import annotations

from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

from tools.competitor_tools import _parse_market_context
from tools.financial_tools import analise_financeira_a4_completo

# área-âncora (ponto médio "M") por tipo de negócio — quando area_min/max não vêm.
_AREA_M_DEFAULT = {"academia": 1150.0, "crossfit_box": 650.0, "studio_pilates": 215.0,
                   "studio_funcional": 475.0, "outro": 900.0}

_GENERO_NOTA = {
    "predominantemente_feminino": "Predominância feminina favorece Mid Market com mix Pilates+Yoga.",
    "predominantemente_masculino": "Predominância masculina favorece Low Cost (musculação/CrossFit).",
    "exclusivamente_feminino": "Nicho exclusivamente feminino: Premium/Mid, mercado ~30% menor.",
    "exclusivamente_masculino": "Nicho exclusivamente masculino é restrito no BR — validar demanda local.",
}


def _loc_do_state(state) -> tuple[str, str, str]:
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


def _derivar_area(ip: dict, tipo: str) -> float:
    a_min = ip.get("area_m2_min") or ip.get("areaMin")
    a_max = ip.get("area_m2_max") or ip.get("areaMax")
    try:
        if a_min and a_max:
            return round((float(a_min) + float(a_max)) / 2, 1)
    except (TypeError, ValueError):
        pass
    return _AREA_M_DEFAULT.get((tipo or "academia").strip().lower(), 1150.0)


def _top1_latlng(state) -> tuple[float | None, float | None]:
    geo = state.get("candidatos_geoscout_pronto") or state.get("candidatos_geoscout") or {}
    cands = geo.get("candidatos") if isinstance(geo, dict) else None
    if not isinstance(cands, list) or not cands:
        return None, None
    c = cands[0] if isinstance(cands[0], dict) else {}
    ll = c.get("latlng") or c.get("location") or {}
    lat = c.get("lat") or (ll.get("lat") if isinstance(ll, dict) else None)
    lng = c.get("lng") or (ll.get("lng") if isinstance(ll, dict) else None)
    return lat, lng


def _justificativa_det(r: dict, bairro: str, genero: str) -> str:
    """Justificativa por TEMPLATE dos campos estruturados — determinística (sem LLM)."""
    modelo = (r.get("recomendacao_modelo") or "").strip() or "—"
    cen = r.get("cenarios") if isinstance(r.get("cenarios"), dict) else {}
    rec = None
    for c in cen.values():
        if isinstance(c, dict) and (c.get("modelo") or "").strip().lower() == modelo.lower():
            rec = c
            break
    partes = [f"{bairro or 'Bairro'}: modelo {modelo} recomendado"]
    if rec:
        det = []
        mg = rec.get("margem_percentual")
        pb = rec.get("payback_meses")
        if mg is not None:
            det.append(f"margem {mg}%")
        if pb is not None:
            det.append(f"payback {pb}m")
        if det:
            partes[0] += " (" + ", ".join(det) + ")"
    partes[0] += "."
    nota = _GENERO_NOTA.get((genero or "misto").strip().lower())
    if nota:
        partes.append(nota)
    return " ".join(partes)


class FinancialEstimatorAgent(BaseAgent):
    """A4 determinístico: roda a macro financeira + justificativa por template."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        cidade, uf, bairro = _loc_do_state(state)
        ip = state.get("input_params") if isinstance(state.get("input_params"), dict) else {}
        mc = _parse_market_context(state.get("market_context"))
        mci = (mc.get("market_context") if isinstance(mc, dict) and isinstance(mc.get("market_context"), dict) else mc) or {}
        tipo = (ip.get("tipo_negocio") or mci.get("tipo_negocio") or "academia")
        tamanho = (ip.get("tamanho_preset") or mci.get("tamanho_preset") or "m")
        genero = (ip.get("genero_alvo") or mci.get("genero_alvo") or "misto")
        area_m2 = _derivar_area(ip, tipo)
        lat, lng = _top1_latlng(state)
        tipo_obra = ip.get("tipo_obra") or ip.get("tipoObra") or mci.get("tipo_obra")
        reforco = ip.get("necessita_reforco_estrutural") or ip.get("reforcoEstrutural")
        if reforco is None:
            reforco = mci.get("necessita_reforco_estrutural")

        try:
            # macro é async (faz aluguel + viabilidade); MRLR é Tier 0 primário lá dentro
            r = await analise_financeira_a4_completo(
                bairro, cidade, uf, area_m2,
                area_m2_min=int(ip.get("area_m2_min") or 1000),
                area_m2_max=int(ip.get("area_m2_max") or 1500),
                tipo_negocio=tipo, tamanho_preset=tamanho,
                destino_lat=lat, destino_lng=lng,
                tipo_obra=str(tipo_obra or "adaptacao"),
                necessita_reforco_estrutural=bool(reforco),
            )
            if not isinstance(r, dict):
                r = {"erro": "macro retornou não-dict", "score_viabilidade": None}
            else:
                r["justificativa"] = _justificativa_det(r, bairro, genero)
        except Exception as e:  # nunca derruba o pipeline
            r = {"erro": f"{type(e).__name__}: {e}", "score_viabilidade": None}

        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            actions=EventActions(state_delta={
                "analise_financeira_pronto": r,   # A6 lê os números direto (auditável)
                "analise_financeira": r,           # output_key legado
            }),
        )


financial_estimator_agent = FinancialEstimatorAgent(
    name="FinancialEstimator",
    description=(
        "A4 determinístico (sem LLM): viabilidade financeira 3 cenários (low/mid/premium) "
        "com aluguel MRLR determinístico, CAPEX, payback, margem e recomendação."
    ),
)
