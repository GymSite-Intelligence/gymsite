"""PDF normalizado no layout Cocó (weasy) + placeholder do prompt A0 não vaza.

Divergência que motivou: relatório Pirapora saiu no layout ReportLab (seções
numeradas, sem rodapé Confidencial) e com literais do schema do prompt A0
("fato+fonte 1", "crescimento|estavel|retracao") impressos como dado.
"""
from __future__ import annotations

import inspect

from pdf.adapters import _map_market


def test_endpoint_pdf_default_engine_weasy():
    """Acesso direto ao endpoint (sem ?engine=) deve dar o layout de produção."""
    import api

    sig = inspect.signature(api.get_relatorio_pdf)
    assert sig.parameters["engine"].default == "weasy"


def test_placeholder_insights_a0_nao_vaza():
    mc = {
        "insights_estrategicos": ["fato+fonte 1", "fato+fonte 2", "fato+fonte 3"],
    }
    assert _map_market(mc).insights == []


def test_placeholder_tendencia_a0_nao_vaza():
    mc = {"tendencia_mercado": "crescimento|estavel|retracao"}
    assert _map_market(mc).tendencia is None


def test_placeholder_data_coleta_nao_vaza():
    mc = {"aluguel_medio_m2": "YYYY-MM-DD"}
    assert _map_market(mc).aluguel_m2 is None


def test_map_market_baixas_e_carimbo():
    mc = {
        "parque_ativo_total": 100,
        "novos_cnpj_fitness_90d": 10,
        "baixas_cnpj_fitness_90d": 3,
        "baixas_cnpj_fitness_q": 5,
        "entrantes_cnpj_fitness_q": 12,
        "saldo_oferta_q": 7,
        "pressao_oferta_q": "expansao",
        "janela_q_label": "2026-Q1",
        "cnpj_as_of": "2026-05-31",
        "arvore_oferta": {
            "baixas_bairro_q": 2,
            "ref_month": "2026-05-01",
        },
    }
    m = _map_market(mc)
    # 90d não entra no PDF cliente — canônico é o trimestre (Q).
    assert m.novos_cnpj_90d is None
    assert m.baixas_cnpj_90d is None
    assert m.baixas_cnpj_q == 5
    assert m.entrantes_cnpj_q == 12
    assert m.saldo_oferta_q == 7
    assert m.pressao_oferta_q == "expansao"
    assert m.janela_q_label == "2026-Q1"
    assert m.cnpj_as_of == "2026-05-31"
    assert m.baixas_bairro_q == 2
    assert m.ref_month_cnpj == "2026-05-01"


def test_insight_real_preservado():
    mc = {
        "insights_estrategicos": [
            "Parque de 46 CNPJ ativos (RFB, 2026-08)",
            "fato+fonte 2",
        ],
        "tendencia_mercado": "estavel",
    }
    m = _map_market(mc)
    assert m.insights == ["Parque de 46 CNPJ ativos (RFB, 2026-08)"]
    assert m.tendencia == "estavel"
