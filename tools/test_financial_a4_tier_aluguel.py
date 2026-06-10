"""Testes — cascata Tier 1 portais vazio → Tier 2 Grounding + macro BCB (mock)."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from tools.aluguel_municipio_portais import MIN_SAMPLES_ALTA
from tools.financial_tools import analise_financeira_a4_completo


@pytest.mark.asyncio
async def test_a4_tier1_vazio_usa_grounding_e_bcb(monkeypatch: Any) -> None:
    municipio_vazio = {
        "tier1_suficiente": False,
        "n_validos": 0,
        "mediana_r_m2": 0.0,
        "min_r_m2": 0.0,
        "max_r_m2": 0.0,
        "confianca": "baixa",
        "classificacao": "sem_dados",
        "aviso": "Nenhum anúncio com preço e área válidos nos portais consultados.",
        "urls_consultadas": {"zap": ["u1"], "viva": [], "olx": []},
        "erros": ["zap: timeout"],
        "aluguel_municipio_referencia": {"n_amostras": 0},
        "faixa_rs_m2": {"mediana": 0.0, "p25": 0.0, "p75": 0.0},
    }
    grounding = {
        "mediana_r_m2": 42.0,
        "min_r_m2": 35.0,
        "max_r_m2": 55.0,
        "queries_com_dados": 2,
        "valores_coletados": [38.0, 42.0, 48.0],
        "fontes": [{"query": "aluguel comercial", "n_valores": 2}],
    }
    bcb = {
        "ok": True,
        "norte": "Referência macro imobiliária (BCB/Olinda).",
        "destaques": {"financiamento_residencial": {"valor": 100.0, "data": "2025-01-01"}},
    }

    with (
        patch(
            "tools.aluguel_municipio_portais.pesquisar_aluguel_municipio",
            new_callable=AsyncMock,
            return_value=municipio_vazio,
        ),
        patch(
            "tools.gemini_search_grounding.pesquisar_aluguel_mediana",
            new_callable=AsyncMock,
            return_value=grounding,
        ),
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

    det = fin["aluguel_pesquisa_detalhes"]
    assert det["tier"] == 2
    assert det["tier1_vazio"] is True
    assert det["n_validos_tier1"] == 0
    assert det["motivo_tier1"]
    assert "Search Grounding" in fin["fonte_aluguel"]
    assert "portais" in fin["aviso_metodologia_aluguel"].lower()
    assert fin["referencia_macro_bcb"]["ok"] is True
    assert any("Search Grounding" in a for a in fin.get("alertas", []))


@pytest.mark.asyncio
async def test_a4_tier1_ok_sem_bcb(monkeypatch: Any) -> None:
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
        patch(
            "tools.aluguel_municipio_portais.pesquisar_aluguel_municipio",
            new_callable=AsyncMock,
            return_value=municipio_ok,
        ),
        patch(
            "tools.gemini_search_grounding.pesquisar_aluguel_mediana",
            new_callable=AsyncMock,
        ) as mock_g,
        patch("tools.bcb_imobiliario_olinda.extrair_resumo_imobiliario") as mock_bcb,
    ):
        fin = await analise_financeira_a4_completo(
            bairro="Centro",
            cidade="Fortaleza",
            uf="CE",
            area_m2=1000.0,
        )

    mock_g.assert_not_called()
    mock_bcb.assert_not_called()
    assert fin["aluguel_pesquisa_detalhes"]["tier"] == 1
    assert fin["referencia_macro_bcb"] is None
    assert "Portais municipais" in fin["fonte_aluguel"]
