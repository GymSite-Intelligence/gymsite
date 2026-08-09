"""Facades RAG: Eros antes de Vertex; sem vazamento de billing."""
from __future__ import annotations

import os
from unittest.mock import patch

from agents_site.tools import (
    _pack_eros_as_resultados,
    consultar_base_regulatoria,
    consultar_catalogo_equipamentos,
    consultar_engenharia_obra,
)


def test_pack_eros_from_texto_only():
    packed = _pack_eros_as_resultados(
        {"texto_rag": "CREF PJ obrigatório", "fontes": [], "n_docs": 0},
        "Eros RAG (test)",
    )
    assert packed is not None
    assert packed["n_docs"] >= 1
    assert "CREF" in packed["resultados"][0]["trecho"]


def test_pack_eros_vazio():
    assert _pack_eros_as_resultados({"texto_rag": "", "fontes": [], "n_docs": 0}, "x") is None


def test_regulatoria_usa_eros_quando_grupo_set():
    fake = {
        "texto_rag": "Lei 9.696 exige registro CREF.",
        "fontes": [{"title": "Lei", "snippet": "registro CREF PJ"}],
        "n_docs": 1,
    }
    with patch.dict(os.environ, {"EROS_GROUP_ID_REGULATORIO": "uuid-reg"}, clear=False):
        with patch("agents_site.tools_l2_rag.consultar_eros_regulatorio", return_value=fake):
            r = consultar_base_regulatoria("CREF academia")
    assert r["n_docs"] >= 1
    assert "Eros" in (r.get("canal_retrieval") or r.get("fonte") or "")


def test_engenharia_usa_eros_quando_grupo_set():
    fake = {
        "texto_rag": "NBR 6120 carga 5 kN/m2 academia.",
        "fontes": [{"title": "NBR 6120", "snippet": "5 kN/m2"}],
        "n_docs": 1,
    }
    with patch.dict(os.environ, {"EROS_GROUP_ID_ENGENHARIA": "uuid-eng"}, clear=False):
        with patch("agents_site.tools_l2_rag.consultar_eros_engenharia", return_value=fake):
            r = consultar_engenharia_obra("carga de laje academia")
    assert r["n_docs"] >= 1
    assert "Eros" in (r.get("canal_retrieval") or r.get("fonte") or "")


def test_catalogo_sem_tecnico_nao_exige_eros():
    with patch.dict(os.environ, {"EROS_GROUP_ID_TECNICO": "", "VERTEX_RAG_ENABLED": "0"}, clear=False):
        with patch("tools.discovery_engine_tools.buscar_catalogos_equipamentos") as mock_v:
            r = consultar_catalogo_equipamentos("esteira Matrix")
            mock_v.assert_not_called()
    raw = str(r).lower()
    assert "billing" not in raw
    assert "vertex" not in (r.get("fonte") or "").lower()
    # corpus local técnico pode devolver n_docs>0; stub vazio também ok
    assert "n_docs" in r
