"""Cascata ZEUS — nunca assume PERMISSIVO sem malha oficial."""
from __future__ import annotations

from unittest.mock import patch

from tools.zoneamento_tools import (
    _bloco_indisponivel,
    _bloco_proxy_osm,
    analisar_zoneamento_candidato,
)


def test_indisponivel_nunca_permissivo():
    out = _bloco_indisponivel("Campinas", "Cambuí", "SP", -22.9, -47.0, "9313-1/00")
    assert out["status"] == "indisponivel"
    assert out["compatibilidade"] is None
    assert "prefeitura" in (out["alerta"] or "").lower()
    assert out["fonte_dados"] is None


def test_proxy_osm_rotula_individualizar():
    out = _bloco_proxy_osm(
        "Niterói", "Icaraí", "RJ", -22.9, -43.1, "9313-1/00", "residential")
    assert out["status"] == "proxy_osm"
    assert out["compatibilidade"] == "INDIVIDUALIZAR"
    assert out["uso_predominante_osm"] == "residential"
    assert "observado" in (out.get("uso_observado") or "")
    assert out["fonte_dados"] == "OSM_landuse_proxy"
    assert "prefeitura" in (out["alerta"] or "").lower()


def test_municipio_sem_adapter_cai_proxy_ou_indisponivel():
    """Sem CKAN cadastrado: OSM ou indisponível — nunca PERMISSIVO inventado."""
    with patch("tools.zoneamento_tools._municipio_cfg", return_value=None), \
         patch("tools.zeus_osm_proxy.consultar_osm_proxy", return_value=None):
        out = analisar_zoneamento_candidato(
            "Cidade Sem Dados", "Centro", "XX", -15.0, -48.0)
    assert out["status"] == "indisponivel"
    assert out["compatibilidade"] is None
    assert out.get("compatibilidade") != "PERMISSIVO"
    assert "prefeitura" in (out["alerta"] or "").lower()


def test_municipio_sem_adapter_com_osm():
    perfil = {
        "tag_osm": "commercial",
        "uso_observado": "comercial_observado",
        "origem_tag": "landuse",
        "n_features": 5,
        "completude": "alta",
        "confianca": 85,
    }
    with patch("tools.zoneamento_tools._municipio_cfg", return_value=None), \
         patch("tools.zeus_osm_proxy.consultar_osm_proxy", return_value=perfil):
        out = analisar_zoneamento_candidato(
            "Lagoa", "Barra da Tijuca", "RJ", -23.0, -43.3)
    assert out["status"] == "proxy_osm"
    assert out["compatibilidade"] == "INDIVIDUALIZAR"
    assert out["uso_predominante_osm"] == "commercial"
    assert out["uso_observado"] == "comercial_observado"


def test_ckan_fora_de_zona_rotula_permissivo_com_fonte():
    """PERMISSIVO só com malha CKAN (fora de zona especial = uso geral)."""
    import tools.zoneamento_tools as zt

    zt._polygons_cache.clear()
    fake_poly = [{"polygon": [(-38.5, -3.8), (-38.4, -3.8), (-38.4, -3.7), (-38.5, -3.7)],
                  "sigla_zona": "ZEIS"}]
    cfg = {"ckan_base": "https://example", "dataset_zonas": "zonas", "subgrupos": ["SE"]}
    with patch("tools.zoneamento_tools._municipio_cfg", return_value=cfg), \
         patch("tools.zoneamento_tools._fetch_kmz", return_value=b"fake"), \
         patch("tools.zoneamento_tools._parse_kmz_to_polygons", return_value=fake_poly), \
         patch("tools.zoneamento_tools._svg_mapa_zonas", return_value=None), \
         patch("tools.zoneamento_tools._png_mapa_zonas", return_value=None):
        # ponto longe do polígono ZEIS → fora_de_zona
        out = analisar_zoneamento_candidato(
            "Fortaleza", "Cocó", "CE", -3.50, -38.20)
    assert out["status"] == "fora_de_zona"
    assert out["compatibilidade"] == "PERMISSIVO"
    assert out["fonte_dados"] == "CKAN_FORTALEZA"
    assert out["camada"] == "ckan_municipal"


def test_ckan_falha_nao_assume_permissivo():
    import tools.zoneamento_tools as zt

    zt._polygons_cache.clear()
    cfg = {"ckan_base": "https://example", "dataset_zonas": "zonas"}
    with patch("tools.zoneamento_tools._municipio_cfg", return_value=cfg), \
         patch("tools.zoneamento_tools._fetch_kmz", return_value=None), \
         patch("tools.zeus_osm_proxy.consultar_osm_proxy", return_value=None):
        out = analisar_zoneamento_candidato(
            "Fortaleza", "Meireles", "CE", -3.73, -38.49)
    assert out["status"] == "indisponivel"
    assert out["compatibilidade"] is None


def test_pdf_mostra_indisponivel_e_proxy():
    import json
    from pathlib import Path

    from pdf.adapters import relatorio_from_nested_json
    from pdf.html_builder import gerar_html

    d = json.loads(Path("metrics/relatorios/rpt_1786416027.json").read_text(encoding="utf-8"))
    out = d["output_consolidado"]

    out["zoneamento"] = {
        "status": "indisponivel",
        "compatibilidade": None,
        "alerta": "Avaliar uso e ocupação do solo junto à prefeitura do município.",
        "descricao": "Sem plano diretor/LUOS digital.",
        "cnae": "9313-1/00",
    }
    html = gerar_html(relatorio_from_nested_json(d))
    assert "Análise de zoneamento urbano" in html
    assert "INDISPONÍVEL" in html
    assert "prefeitura" in html.lower()
    assert "Não se assume permissividade" in html or "prefeitura" in html.lower()

    out["zoneamento"] = {
        "status": "proxy_osm",
        "compatibilidade": "INDIVIDUALIZAR",
        "uso_predominante_osm": "residential",
        "uso_observado": "residencial_observado",
        "zona_sigla": "OSM:residential",
        "alerta": "Avaliar junto à prefeitura do município.",
        "descricao": "Uso OBSERVADO no OSM — não é zoneamento legal.",
        "fonte_dados": "OSM_landuse_proxy",
        "confianca": 85,
        "completude": "alta",
        "cnae": "9313-1/00",
    }
    html2 = gerar_html(relatorio_from_nested_json(d))
    assert "INDIVIDUALIZAR" in html2
    assert "residencial_observado" in html2 or "residential" in html2
    assert "prefeitura" in html2.lower()
    assert "OBSERVADO" in html2 or "observado" in html2.lower()
