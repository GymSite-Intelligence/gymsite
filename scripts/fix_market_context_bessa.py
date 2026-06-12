# -*- coding: utf-8 -*-
"""
Correção pontual do market_context do relatório Bessa (12/06/2026).

Três defeitos do quadro "Contexto de Mercado" gerado pré-fix:
1. parque 0 — bug de acento no match de cidade (LLM chamou "Joao Pessoa");
   corrigido em tools/cnpj_fitness_tools.py (_cidade_canonica). Aqui: backfill.
2. aluguel_medio_m2 com preço de VENDA (R$ 6.846/m², grounding confundiu);
   substituído pela mediana de LOCAÇÃO do market_bundle (16 anúncios, URLs).
3. ticket_medio_mercado "R$ 599-3.700" — dado NACIONAL de academias premium
   (Kimi) promovido a ticket local; substituído pela faixa dos planos
   públicos dos concorrentes do próprio relatório (auditável).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv(override=True)

from supabase import create_client

from tools.cnpj_fitness_tools import composicao_parque_cnpj, resumo_cnpj_fitness

RELATORIO = "25207ce4-705f-4925-84c3-32aa80600900"

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

comp = composicao_parque_cnpj("João Pessoa", "PB")
resumo = resumo_cnpj_fitness("João Pessoa", "PB", 90)

row = (
    sb.table("relatorio_outputs")
    .select("market_context")
    .eq("relatorio_id", RELATORIO)
    .maybe_single()
    .execute()
)
mc = (row.data or {}).get("market_context") or {}

mc.update({
    "parque_ativo_total": comp.get("total"),
    "parque_comercial_total": comp.get("parque_comercial_total"),
    "excluidos_saude_clinica": comp.get("excluidos_saude_clinica"),
    "pendentes_validacao": comp.get("pendentes_validacao"),
    "composicao_parque": comp.get("composicao_parque") or {},
    "academias_ativas_cidade_cnpj": comp.get("total"),
    "novos_cnpj_fitness_90d": resumo.get("novos_cnpj_fitness_90d"),
    "novas_unidades_90d_por_segmento": resumo.get("novas_unidades_90d_por_segmento") or {},
    "fonte_entrantes": "RFB CNPJ Aberto (snapshot mensal, via Supabase)",
    "aluguel_medio_m2": (
        "R$ 46–63/m² locação (mediana R$ 58/m² — 16 anúncios OLX João Pessoa, "
        "proxy residencial; norte de mercado, não cotação)"
    ),
    "ticket_medio_mercado": (
        "R$ 60 a R$ 350/mês (faixa dos planos públicos dos concorrentes do "
        "raio — Dinâmica R$ 59,90 a Korpus R$ 349,99)"
    ),
})

insights = [
    i for i in (mc.get("insights_estrategicos") or [])
    if "R$ 599" not in i
]
insights.append(
    "Parque de 639 unidades fitness ativas em João Pessoa (433 academias "
    "tradicionais) com 22 aberturas nos últimos 90 dias — mercado em expansão "
    "(RFB CNPJ Aberto)."
)
mc["insights_estrategicos"] = insights

fp = mc.get("fatos_parque_cnpj") or {}
fp["fonte"] = "RFB CNPJ Aberto"
fp["metricas"] = {
    "parque_ativo_total": comp.get("total"),
    "parque_comercial_total": comp.get("parque_comercial_total"),
    "novos_cnpj_fitness_90d": resumo.get("novos_cnpj_fitness_90d"),
}
mc["fatos_parque_cnpj"] = fp

sb.table("relatorio_outputs").update({"market_context": mc}).eq(
    "relatorio_id", RELATORIO
).execute()
print("market_context atualizado:")
print("  parque:", mc["parque_ativo_total"], "| novos 90d:", mc["novos_cnpj_fitness_90d"])
print("  aluguel:", mc["aluguel_medio_m2"][:60])
print("  ticket:", mc["ticket_medio_mercado"][:60])
