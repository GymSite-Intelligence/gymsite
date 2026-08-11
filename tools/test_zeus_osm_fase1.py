"""ZEUS Fase 1 — motor OSM (observado) + completude + top-20 âncoras."""
from __future__ import annotations

from unittest.mock import patch

from tools.zeus_osm_proxy import (
    TOP20_MUNICIPIOS_VALIDACAO,
    avaliar_completude,
    invariantes_proxy,
    rotular_uso_observado,
)
from tools.zoneamento_tools import _bloco_proxy_osm, analisar_zoneamento_candidato


def test_rotulo_nunca_e_veredito_legal():
    for tag in ("commercial", "residential", "industrial", "retail"):
        lab = rotular_uso_observado(tag)
        assert "PERMISSIVO" not in lab.upper()
        assert "CONDICIONADO" not in lab.upper()
        assert "RESTRITO" not in lab.upper()
        assert "observado" in lab


def test_completude_alta_e_baixa():
    alta = avaliar_completude(5)
    assert alta["completude"] == "alta"
    assert alta["confianca"] == 85
    assert alta["nota_completude"] is None

    baixa = avaliar_completude(1)
    assert baixa["completude"] == "baixa"
    assert baixa["confianca"] == 40
    assert "esparsos" in (baixa["nota_completude"] or "").lower()

    zero = avaliar_completude(0)
    assert zero["confianca"] == 0


def test_bloco_proxy_semantica_observado_e_confianca():
    out = _bloco_proxy_osm(
        "Campinas", "Cambuí", "SP", -22.9, -47.0, "9313-1/00", "commercial",
        perfil={
            "tag_osm": "commercial",
            "uso_observado": "comercial_observado",
            "origem_tag": "landuse",
            "n_features": 8,
            "completude": "alta",
            "confianca": 85,
        },
    )
    assert out["compatibilidade"] == "INDIVIDUALIZAR"
    assert out["uso_observado"] == "comercial_observado"
    assert "OBSERVADO" in out["descricao"] or "observado" in out["descricao"].lower()
    assert "permit" not in out["descricao"].lower() or "NÃO" in out["descricao"]
    assert out["confianca"] == 85
    assert invariantes_proxy(out) == []


def test_bloco_proxy_baixa_completude_alerta():
    out = _bloco_proxy_osm(
        "X", "Y", "ZZ", -10.0, -50.0, "9313-1/00", "residential",
        perfil={
            "tag_osm": "residential",
            "uso_observado": "residencial_observado",
            "n_features": 1,
            "completude": "baixa",
            "confianca": 40,
            "nota_completude": "Dados do OSM nesta área são esparsos; verificação em campo.",
        },
    )
    assert out["baixa_completude"] is True
    assert "esparsos" in (out["alerta"] or "").lower()


def test_cascata_usa_perfil_osm_completo():
    perfil = {
        "tag_osm": "retail",
        "origem_tag": "landuse",
        "uso_observado": "comercial_observado",
        "n_features": 4,
        "completude": "alta",
        "confianca": 85,
        "landuse_counts": {"retail": 4},
        "zoning_counts": {},
        "raio_m": 150,
    }
    with patch("tools.zoneamento_tools._municipio_cfg", return_value=None), \
         patch("tools.zeus_osm_proxy.consultar_osm_proxy", return_value=perfil):
        out = analisar_zoneamento_candidato(
            "Guarulhos", "Centro", "SP", -23.45, -46.53)
    assert out["status"] == "proxy_osm"
    assert out["compatibilidade"] == "INDIVIDUALIZAR"
    assert out["uso_observado"] == "comercial_observado"
    assert out["confianca"] == 85


def test_top20_ancoras_completas():
    assert len(TOP20_MUNICIPIOS_VALIDACAO) == 20
    assert TOP20_MUNICIPIOS_VALIDACAO[0]["cidade"] == "São Paulo"
    assert any(m.get("tem_ckan") for m in TOP20_MUNICIPIOS_VALIDACAO)
    for m in TOP20_MUNICIPIOS_VALIDACAO:
        assert m["lat"] is not None and m["lon"] is not None
        assert m["uf"]
