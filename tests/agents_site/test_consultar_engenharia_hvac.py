"""Engenheiro — HVAC query boost via 2ª chamada Eros (sem Discovery)."""
from __future__ import annotations

import os
from unittest.mock import patch

from agents_site.tools import consultar_engenharia_obra


def test_hvac_segunda_query_quando_primeiro_trecho_e_piso():
    off = {
        "texto_rag": "Espessura de piso emborrachado 15 mm a 16 mm — PISO PADRÃO DE ACADEMIA.",
        "fontes": [
            {
                "title": "engenharia_normas_obra_projeto_ref",
                "snippet": "Espessura de piso emborrachado 15 mm a 16 mm — PISO PADRÃO DE ACADEMIA.",
            }
        ],
        "n_docs": 1,
    }
    on = {
        "texto_rag": "Vazão NBR 16401-3: 5,0 l/s por pessoa + 0,6 l/s por m². PMOC obrigatório.",
        "fontes": [
            {
                "title": "engenharia_climatizacao_academia_ref",
                "snippet": "Vazão NBR 16401-3: 5,0 l/s por pessoa + 0,6 l/s por m². PMOC obrigatório.",
            }
        ],
        "n_docs": 1,
    }

    with patch.dict(os.environ, {"EROS_GROUP_ID_ENGENHARIA": "uuid-eng"}, clear=False):
        with patch(
            "agents_site.tools_l2_rag.consultar_eros_engenharia",
            side_effect=[off, on],
        ) as mock_eros:
            with patch(
                "agents_site.carimbo.anotar_retrieval_legal",
                side_effect=lambda r, *_a, **_k: r,
            ):
                r = consultar_engenharia_obra(
                    "como projetar refrigeracao sala coletivas 100 m2"
                )

    assert mock_eros.call_count == 2
    assert r["n_docs"] >= 1
    blob = " ".join(
        (d.get("trecho") or "") for d in (r.get("resultados") or [])
    ).lower()
    blob += " " + (r.get("texto_rag") or "").lower()
    assert "16401" in blob or "vazão" in blob or "vazao" in blob or "pmoc" in blob


def test_hvac_sempre_dispara_segunda_query():
    hit = {
        "texto_rag": "sala 100 m² → ~28 pessoas no pico.",
        "fontes": [{"title": "clima", "snippet": "sala 100 m² → ~28 pessoas no pico."}],
        "n_docs": 1,
    }
    boost = {
        "texto_rag": "NBR 16401-3 vazão 5,0 l/s por pessoa + 0,6 l/s por m². PMOC.",
        "fontes": [
            {
                "title": "engenharia_climatizacao_academia_ref",
                "snippet": "NBR 16401-3 vazão 5,0 l/s por pessoa + 0,6 l/s por m². PMOC.",
            }
        ],
        "n_docs": 1,
    }
    with patch.dict(os.environ, {"EROS_GROUP_ID_ENGENHARIA": "uuid-eng"}, clear=False):
        with patch(
            "agents_site.tools_l2_rag.consultar_eros_engenharia",
            side_effect=[hit, boost],
        ) as mock_eros:
            with patch(
                "agents_site.carimbo.anotar_retrieval_legal",
                side_effect=lambda r, *_a, **_k: r,
            ):
                r = consultar_engenharia_obra("climatizacao academia NBR 16401")
    assert mock_eros.call_count == 2
    blob = ((r.get("texto_rag") or "") + " ".join(
        d.get("trecho") or "" for d in (r.get("resultados") or [])
    )).lower()
    assert "16401" in blob
