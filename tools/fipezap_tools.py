# tools/fipezap_tools.py
"""
Lookup de índices FipeZap no Supabase.

Usado pelo A4 FinancialEstimator como Tier 1.5 de aluguel:
  Tier 1: Search Grounding (ao vivo)
  Tier 1.5: FipeZap (dados mensais oficiais do mercado)
  Tier 2: Benchmarks ACAD hardcoded

Tabela: `fipezap_indices` (atualizada mensal via tools/fipezap_loader.py)
"""

from __future__ import annotations

import logging
import os
from datetime import date
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

logger = logging.getLogger("fipezap_tools")


def _get_client() -> Client | None:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)


def get_ultimo_indice(
    cidade: str,
    tipo_indice: str = "locacao_comercial",
) -> dict[str, Any] | None:
    """
    Retorna o registro mais recente do FipeZap para a cidade + tipo.

    Args:
        cidade: nome da cidade (ex: "São Paulo", "Fortaleza")
        tipo_indice: um de venda_residencial | locacao_residencial |
                     rentabilidade_residencial | venda_comercial |
                     locacao_comercial | rentabilidade_comercial

    Returns:
        Dict com preco_medio_m2, variacao_mensal_pct, variacao_12m_pct,
        data_referencia, etc. Ou None se não houver dados.
    """
    supabase = _get_client()
    if supabase is None:
        logger.warning("Supabase não configurado — pulando lookup FipeZap")
        return None

    try:
        resp = (
            supabase.table("fipezap_indices")
            .select("*")
            .eq("cidade", cidade)
            .eq("tipo_indice", tipo_indice)
            .order("data_referencia", desc=True)
            .limit(1)
            .execute()
        )
        if resp.data:
            return resp.data[0]
    except Exception as exc:
        logger.warning("Erro ao consultar fipezap_indices: %s", exc)

    return None


def get_aluguel_comercial_m2(cidade: str) -> dict[str, Any]:
    """
    Wrapper prático pro A4: retorna o preço/m² de locação comercial
    mais recente + metadados.

    Returns:
        {
            "preco_m2": float | None,
            "data_referencia": str | None,
            "variacao_12m_pct": float | None,
            "fonte": str,
            "disponivel": bool,
        }
    """
    reg = get_ultimo_indice(cidade, tipo_indice="locacao_comercial")
    if reg:
        return {
            "preco_m2": reg.get("preco_medio_m2"),
            "data_referencia": reg.get("data_referencia"),
            "variacao_12m_pct": reg.get("variacao_12m_pct"),
            "variacao_mensal_pct": reg.get("variacao_mensal_pct"),
            "fonte": f"FipeZap Comercial ({reg.get('data_referencia')})",
            "disponivel": True,
        }

    # Fallback: tenta locação residencial e aplica fator de conversão
    reg_res = get_ultimo_indice(cidade, tipo_indice="locacao_residencial")
    if reg_res:
        preco_res = reg_res.get("preco_medio_m2")
        # Fator empírico comercial/residencial baseado nas 10 cidades onde
        # ambos existem (média ~1,35x). Usado só como proxy quando não há
        # índice comercial direto (ex: Fortaleza tem residencial mas não
        # comercial no FipeZap tradicional — mas na planilha série histórica
        # completa, Fortaleza aparece com dados residenciais).
        fator = 1.35
        return {
            "preco_m2": round(preco_res * fator, 2) if preco_res else None,
            "data_referencia": reg_res.get("data_referencia"),
            "variacao_12m_pct": reg_res.get("variacao_12m_pct"),
            "variacao_mensal_pct": reg_res.get("variacao_mensal_pct"),
            "fonte": f"FipeZap Residencial proxy ×{fator} ({reg_res.get('data_referencia')})",
            "disponivel": True,
        }

    return {
        "preco_m2": None,
        "data_referencia": None,
        "variacao_12m_pct": None,
        "variacao_mensal_pct": None,
        "fonte": "FipeZap não disponível",
        "disponivel": False,
    }


def get_variacao_12m(cidade: str, tipo_indice: str = "locacao_comercial") -> float | None:
    """Retorna a variação acumulada em 12 meses (%) ou None."""
    reg = get_ultimo_indice(cidade, tipo_indice)
    return reg.get("variacao_12m_pct") if reg else None
