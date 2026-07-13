"""Testes — cascata aluguel A4 (MRLR-first, P-000)."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools.aluguel_municipio_portais import MIN_SAMPLES_ALTA
from tools.financial_tools import analise_financeira_a4_completo


@pytest.mark.asyncio
async def test_a4_mrlr_ok_nao_chama_portais(monkeypatch: Any) -> None:
    mrlr = {
        "status": "ok",
        "valor_unitario_m2": 55.0,
        "fonte": "MRLR IBAPE-GO",
        "inputs": {"area_m2": 1000},
    }
    with (
        patch("tools.aluguel_mrlr.aluguel_deterministico", return_value=mrlr),
        patch(
            "tools.aluguel_municipio_portais.pesquisar_aluguel_municipio",
            new_callable=AsyncMock,
        ) as mock_portais,
    ):
        fin = await analise_financeira_a4_completo(
            bairro="Cocó",
            cidade="Fortaleza",
            uf="CE",
            area_m2=1000.0,
        )

    mock_portais.assert_not_called()
    assert fin["aluguel_pesquisa_detalhes"]["tier"] == 0
    assert fin["aluguel_deterministico"] is True
    assert "MRLR" in fin["fonte_aluguel"]


@pytest.mark.asyncio
async def test_a4_mrlr_fail_usa_benchmark_e_bcb(monkeypatch: Any) -> None:
    municipio_vazio = {
        "tier1_suficiente": False,
        "n_validos": 0,
        "mediana_r_m2": 0.0,
        "urls_consultadas": {"zap": ["u1"]},
        "erros": ["zap: timeout"],
        "aluguel_municipio_referencia": {"n_amostras": 0},
    }
    bcb = {
        "ok": True,
        "norte": "Referência macro imobiliária (BCB/Olinda).",
    }

    with (
        patch("tools.aluguel_mrlr.aluguel_deterministico", return_value={"status": "indisponivel"}),
        patch(
            "tools.aluguel_municipio_portais.pesquisar_aluguel_municipio",
            new_callable=AsyncMock,
            return_value=municipio_vazio,
        ),
        patch(
            "tools.gemini_search_grounding.pesquisar_aluguel_mediana",
            new_callable=AsyncMock,
        ) as mock_g,
        patch(
            "tools.bcb_imobiliario_olinda.extrair_resumo_imobiliario",
            return_value=bcb,
        ),
        patch.dict("os.environ", {"ALUGUEL_PORTAIS_TIER1": "0"}),
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
    assert any("MRLR indisponível" in a for a in fin.get("alertas", []))


@pytest.mark.asyncio
async def test_a4_tier1_ok_quando_portais_habilitados(monkeypatch: Any) -> None:
    municipio_ok = {
        "tier1_suficiente": True,
        "n_validos": MIN_SAMPLES_ALTA,
        "mediana_r_m2": 50.0,
        "min_r_m2": 45.0,
        "max_r_m2": 60.0,
        "norte": "Norte municipal ok",
        "urls_consultadas": {"zap": ["u1", "u2"]},
        "erros": [],
        "aluguel_municipio_referencia": {"n_amostras": MIN_SAMPLES_ALTA},
        "faixa_rs_m2": {"mediana": 50.0, "p25": 45.0, "p75": 60.0},
    }

    with (
        patch("tools.aluguel_mrlr.aluguel_deterministico", return_value={"status": "indisponivel"}),
        patch(
            "tools.aluguel_municipio_portais.pesquisar_aluguel_municipio",
            new_callable=AsyncMock,
            return_value=municipio_ok,
        ),
        patch(
            "tools.gemini_search_grounding.pesquisar_aluguel_mediana",
            new_callable=AsyncMock,
        ) as mock_g,
        patch.dict("os.environ", {"ALUGUEL_PORTAIS_TIER1": "1"}),
    ):
        fin = await analise_financeira_a4_completo(
            bairro="Centro",
            cidade="Fortaleza",
            uf="CE",
            area_m2=1000.0,
        )

    mock_g.assert_not_called()
    assert fin["aluguel_pesquisa_detalhes"]["tier"] == 1
    assert "Portais municipais" in fin["fonte_aluguel"]
