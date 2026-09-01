"""Facades L2 não importam/chamam Discovery no caminho feliz nem no fallback."""
from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _clear_eros_and_vertex(monkeypatch):
    for k in (
        "EROS_GROUP_ID_MERCADO",
        "EROS_GROUP_ID_WELLHUB",
        "EROS_GROUP_ID_TOTALPASS",
        "EROS_GROUP_ID_GURUPASS",
        "EROS_GROUP_ID_REGULATORIO",
        "EROS_GROUP_ID_ENGENHARIA",
        "EROS_GROUP_ID_TECNICO",
        "VERTEX_RAG_ENABLED",
    ):
        monkeypatch.delenv(k, raising=False)


def test_consultar_base_mercado_nao_chama_discovery():
    with patch("tools.discovery_engine_tools.buscar_conhecimento") as mock_v:
        from agents_site import tools as t

        out = t.consultar_base_mercado("tendencia academias brasil")
        mock_v.assert_not_called()
    assert out.get("fonte")
    assert "Vertex" not in str(out.get("fonte", ""))
    assert out.get("n_docs", 0) == 0 or out.get("status") in (
        "deprecated",
        "indisponivel",
        "vazio",
        None,
    )


def test_consultar_catalogo_nao_chama_discovery():
    with patch("tools.discovery_engine_tools.buscar_catalogos_equipamentos") as mock_v:
        from agents_site import tools as t

        out = t.consultar_catalogo_equipamentos("esteira Matrix")
        mock_v.assert_not_called()
    assert "Vertex" not in str(out.get("fonte", ""))
