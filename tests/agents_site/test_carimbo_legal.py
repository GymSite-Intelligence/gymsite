"""Carimbo legal — extração, validação e packing (P-000 §5 / P-002)."""
from __future__ import annotations

from agents_site.carimbo import (
    INSTRUCAO_CARIMBO_LEGAL,
    anotar_retrieval_legal,
    extrair_citacoes,
    pack_citacoes_tool_results,
    remover_carimbos_inline,
    unpack_citacoes_from_msg,
    validar_citacao,
)


def test_instrucao_proibe_slug_e_pede_json():
    assert "PROIBIDO" in INSTRUCAO_CARIMBO_LEGAL
    assert "regulatorio_anuidades" in INSTRUCAO_CARIMBO_LEGAL
    assert '"citacoes"' in INSTRUCAO_CARIMBO_LEGAL
    assert "Res. CONFEF nº 477/2023" in INSTRUCAO_CARIMBO_LEGAL


def test_validar_rejeita_fonte_vertex_slug_e_trecho():
    assert validar_citacao({
        "valor": "30 dias",
        "base": "deferimento CREF",
        "fonte": "Vertex AI Search (regulatório)",
        "janela": "2026",
    }) is None
    assert validar_citacao({
        "valor": "30 dias",
        "base": "deferimento CREF",
        "fonte": "regulatorio_anuidades_processo_2026 (conforme trecho recuperado)",
        "janela": "2026",
    }) is None
    assert validar_citacao({
        "valor": "30 dias",
        "base": "deferimento CREF",
        "fonte": "documento interno",
        "janela": "2026",
    }) is None


def test_validar_aceita_norma_legal():
    c = validar_citacao({
        "valor": "30 dias",
        "base": "deferimento registro PJ no CREF",
        "fonte": "Res. CONFEF nº 477/2023",
        "janela": "2023",
        "url": "https://example.com/res477",
    })
    assert c is not None
    assert c["fonte"] == "Res. CONFEF nº 477/2023"
    assert c["url"].startswith("https://")


def test_remover_carimbo_inline_slug():
    bruto = (
        "O prazo é de até `30 dias · deferimento registro PJ no CREF · "
        "regulatorio_anuidades_processo_2026 (conforme trecho recuperado) · 2026`."
    )
    limpo = remover_carimbos_inline(bruto)
    assert "regulatorio_anuidades" not in limpo
    assert "30 dias" in limpo
    assert "·" not in limpo


def test_extrair_citacoes_json_bom_e_limpa_inline():
    texto = (
        "Prazo até `30 dias · x · regulatorio_anuidades_processo_2026 · 2026`.\n"
        '{"citacoes":['
        '{"valor":"30 dias","base":"deferimento registro PJ CREF","fonte":"Res. CONFEF nº 477/2023","janela":"2023"},'
        '{"valor":"x","base":"y","fonte":"regulatorio_anuidades_processo_2026","janela":"2026"}'
        "]}"
    )
    limpo, cites = extrair_citacoes(texto)
    assert "citacoes" not in limpo
    assert "regulatorio_anuidades" not in limpo
    assert "30 dias" in limpo
    assert len(cites) == 1
    assert cites[0]["fonte"] == "Res. CONFEF nº 477/2023"


def test_pack_unpack_tool_results():
    cites = [{
        "valor": "RT obrigatório",
        "base": "academia PJ",
        "fonte": "Lei nº 9.696/1998",
        "janela": "1998",
    }]
    packed = pack_citacoes_tool_results(cites)
    assert packed is not None
    msg = {"tool_results": packed}
    assert unpack_citacoes_from_msg(msg) == cites


def test_anotar_retrieval_remove_fonte_vertex():
    r = anotar_retrieval_legal(
        {"resultados": [], "n_docs": 0, "fonte": "Vertex AI Search (x)"},
        "Vertex AI Search (regulatório CREF/Lei)",
    )
    assert "fonte" not in r
    assert r["canal_retrieval"].startswith("Vertex")
    assert "477" in r["como_citar"] or "NORMA" in r["como_citar"]
