"""Testes — cascata aluguel A4 (MRLR-first, P-000)."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from tools.financial_tools import analise_financeira_a4_completo


@pytest.mark.asyncio
async def test_a4_mrlr_ok() -> None:
    mrlr = {
        "status": "ok",
        "valor_unitario_m2": 55.0,
        "fonte": "MRLR IBAPE-GO",
        "inputs": {"area_m2": 1000},
    }
    with patch("tools.aluguel_mrlr.aluguel_deterministico", return_value=mrlr):
        fin = await analise_financeira_a4_completo(
            bairro="Cocó",
            cidade="Fortaleza",
            uf="CE",
            area_m2=1000.0,
        )

    assert fin["aluguel_pesquisa_detalhes"]["tier"] == 0
    assert fin["aluguel_deterministico"] is True
    assert "MRLR" in fin["fonte_aluguel"]


@pytest.mark.asyncio
async def test_a4_mrlr_fail_usa_benchmark_e_bcb() -> None:
    bcb = {
        "ok": True,
        "norte": "Referência macro imobiliária (BCB/Olinda).",
    }

    with (
        patch("tools.aluguel_mrlr.aluguel_deterministico", return_value={"status": "indisponivel"}),
        patch(
            "tools.gemini_search_grounding.pesquisar_aluguel_mediana",
            new_callable=AsyncMock,
        ) as mock_g,
        patch(
            "tools.bcb_imobiliario_olinda.extrair_resumo_imobiliario",
            return_value=bcb,
        ),
    ):
        fin = await analise_financeira_a4_completo(
            bairro="Centro",
            cidade="Hortolândia",
            uf="SP",
            area_m2=1200.0,
        )

    mock_g.assert_not_called()
    det = fin["aluguel_pesquisa_detalhes"]
    assert det["tier"] == 3
    assert fin["aluguel_deterministico"] is False
    assert fin["referencia_macro_bcb"]["ok"] is True
    assert "Benchmark" in fin["fonte_aluguel"]
    assert any("MRLR indisponível" in a for a in fin.get("alertas", []))
