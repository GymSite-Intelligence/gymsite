"""Consultor qualitativo: Eros-first, Vertex só com flag legado."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from services.consultor import consultor_engine as ce


@pytest.mark.asyncio
async def test_base_conhecimento_site_usa_eros_nao_vertex():
    fake = {
        "n_docs": 1,
        "resultados": [{"titulo": "Metodologia", "trecho": "saturação por raio"}],
        "fonte": "Eros RAG (mercado)",
    }
    with patch.dict(os.environ, {"VERTEX_RAG_ENABLED": "0"}, clear=False):
        with patch(
            "agents_site.tools_l2_rag.consultar_base_mercado",
            return_value=fake,
        ) as mock_eros:
            with patch("tools.discovery_engine_tools.buscar_conhecimento") as mock_v:
                r = await ce._tool_base_conhecimento(
                    {"pergunta": "tendencia academias"},
                    MagicMock(),
                    modo_site=True,
                )
    mock_v.assert_not_called()
    mock_eros.assert_called_once()
    assert r["n_docs"] == 1
    assert "Eros" in (r.get("fonte") or "")


@pytest.mark.asyncio
async def test_catalogos_usa_eros_nao_vertex():
    fake = {
        "n_docs": 1,
        "resultados": [{"titulo": "Matrix", "trecho": "esteira"}],
        "fonte": "Eros RAG (catálogo equipamentos)",
    }
    with patch.dict(os.environ, {"VERTEX_RAG_ENABLED": "0"}, clear=False):
        with patch(
            "agents_site.tools_l2_rag.consultar_catalogo_equipamentos",
            return_value=fake,
        ) as mock_eros:
            with patch("tools.discovery_engine_tools.buscar_catalogos_equipamentos") as mock_v:
                r = await ce._tool_catalogos_equipamentos(
                    {"pergunta": "esteira Matrix"},
                    MagicMock(),
                )
    mock_v.assert_not_called()
    mock_eros.assert_called_once()
    assert r["n_docs"] == 1
