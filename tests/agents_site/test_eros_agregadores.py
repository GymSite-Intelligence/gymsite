"""Catálogos Eros Wellhub / TotalPass / GuruPass no agente Mercado."""
from __future__ import annotations

import os
from unittest.mock import patch

from agents_site.agregador_share import (
    extract_municipio_share,
    is_share_agregadores,
    share_from_rows,
)
from agents_site.tools_eros import (
    consultar_eros_gurupass,
    consultar_eros_totalpass,
    consultar_eros_wellhub,
)


def test_mercado_expoe_tools_e_prompt_agregadores():
    import agents_site.tools as tools_mod
    from agents_site import agent as agent_mod

    tools = agent_mod.mercado.tools or []
    assert tools_mod.consultar_eros_wellhub in tools
    assert tools_mod.consultar_eros_totalpass in tools
    assert tools_mod.consultar_eros_gurupass in tools
    assert tools_mod.consultar_share_agregadores in tools
    instr = (agent_mod.mercado.instruction or "").lower()
    assert "consultar_share_agregadores" in instr
    assert "consultar_eros_wellhub" in instr
    assert "não peça município" in instr or "nao peca municipio" in instr
    assert "credenciada" in instr
    assert "brasil" in instr
    assert "percentual" in instr
    assert "se a pergunta não trouxer cidade, recorte são paulo" not in instr


def test_share_from_rows_calcula_percentual_por_municipio():
    out = share_from_rows(
        [
            {"municipio": "Fortaleza", "wellhub": 40, "totalpass": 50, "gurupass": 10},
            {"municipio": "Curitiba", "wellhub": 20, "totalpass": 20, "gurupass": 0},
        ]
    )
    assert out["brasil"]["total"] == 140
    assert out["brasil"]["pct"]["wellhub"] == 42.9
    assert out["brasil"]["pct"]["totalpass"] == 50.0
    assert out["brasil"]["pct"]["gurupass"] == 7.1
    assert out["n_municipios"] == 2
    top0 = out["por_municipio_top"][0]
    assert top0["municipio"] == "Fortaleza"
    assert top0["pct_wellhub"] == 40.0
    assert top0["pct_totalpass"] == 50.0
    assert "42.9%" in out["texto_rag"]
    assert "Fortaleza" in out["texto_rag"]


def test_share_from_rows_usa_total_brasil_do_sql():
    out = share_from_rows(
        [{"municipio": "Fortaleza", "wellhub": 40, "totalpass": 50, "gurupass": 10}],
        brasil_override={"wellhub": 20000, "totalpass": 30000, "gurupass": 5000},
        n_municipios_override=1800,
    )
    assert out["brasil"]["total"] == 55000
    assert out["n_municipios"] == 1800
    assert "55000" in out["texto_rag"] or "55.000" in out["texto_rag"] or "20000" in out["texto_rag"]


def test_share_from_rows_avisa_teto_wellhub():
    rows = [
        {"municipio": f"Cidade {i}", "wellhub": 100, "totalpass": 200 + i, "gurupass": 10}
        for i in range(5)
    ]
    out = share_from_rows(rows)
    assert "100 academias por município" in out["texto_rag"]


def test_is_share_agregadores_e_cidade():
    assert is_share_agregadores("informe o market share entre total pass e wellhub")
    assert is_share_agregadores("percentual Wellhub vs TotalPass no Brasil")
    assert not is_share_agregadores("academias TotalPass no Bessa")
    assert extract_municipio_share("share Wellhub Fortaleza") == "Fortaleza"
    assert extract_municipio_share("market share total pass e wellhub") is None


def test_wellhub_envia_group_id_do_env():
    seen: dict = {}

    class _Resp:
        status_code = 200
        content = b'{"text":"Gold em SP","sources":[{"title":"WH"}]}'
        text = '{"text":"Gold em SP","sources":[{"title":"WH"}]}'

        def json(self):
            return {"text": "Gold em SP", "sources": [{"title": "WH"}]}

    def _post(url, headers=None, json=None, timeout=None):
        seen["url"] = url
        seen["json"] = json
        return _Resp()

    with patch.dict(
        os.environ,
        {
            "EROS_GROUP_ID_WELLHUB": "553fa8d6-e3d2-440a-ba0b-867fb5363627",
            "EROS_SUPABASE_URL": "https://eros.example",
            "EROS_SUPABASE_SERVICE_ROLE_KEY": "sk-test",
        },
        clear=False,
    ), patch("agents_site.tools_eros.httpx.post", _post):
        out = consultar_eros_wellhub("academias Wellhub Gold São Paulo")
    assert seen["json"]["groupId"] == "553fa8d6-e3d2-440a-ba0b-867fb5363627"
    assert out.get("n_docs", 0) >= 1
    assert not out.get("erro")


def test_consultar_base_mercado_roteia_totalpass_pro_grupo():
    fake = {
        "texto_rag": "TotalPass TP 2 no Bessa",
        "fontes": [{"title": "TP", "snippet": "Bessa"}],
        "n_docs": 1,
    }
    with patch.dict(
        os.environ,
        {"EROS_GROUP_ID_TOTALPASS": "6ab0c39b-bf81-4840-9dcc-ed5f5cc86117"},
        clear=False,
    ), patch(
        "agents_site.tools_eros.consultar_eros_totalpass", return_value=fake
    ):
        from agents_site.tools_l2_rag import consultar_base_mercado

        out = consultar_base_mercado("academias TotalPass no Bessa")
    assert out["n_docs"] >= 1
    assert out.get("fonte") == "Eros RAG (TotalPass)"


def test_consultar_base_mercado_share_usa_contagem_sql():
    fake = {
        "texto_rag": "Brasil: Wellhub 60 (60.0%) · TotalPass 40 (40.0%)",
        "n_docs": 2,
        "fonte": "Eros catálogo Wellhub + TotalPass + GuruPass",
        "brasil": {"wellhub": 60, "totalpass": 40, "gurupass": 0, "total": 100},
    }
    with patch(
        "agents_site.agregador_share.consultar_share_agregadores", return_value=fake
    ), patch(
        "agents_site.tools_eros.consultar_eros_wellhub",
        side_effect=AssertionError("RAG Wellhub nao deve rodar no share"),
    ), patch(
        "agents_site.tools_eros.consultar_eros_totalpass",
        side_effect=AssertionError("RAG TotalPass nao deve rodar no share"),
    ):
        from agents_site.tools_l2_rag import consultar_base_mercado

        out = consultar_base_mercado("informe o market share entre total pass e wellhub")
    assert out["n_docs"] >= 2
    assert "catálogo" in (out.get("fonte") or "").lower() or "catalogo" in (out.get("fonte") or "").lower()
    assert "60.0%" in (out.get("texto_rag") or "")
