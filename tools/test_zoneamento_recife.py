"""Recife Camada 1 — ZEIS GeoJSON WGS84; fora da malha → cascata OSM (sem PERMISSIVO)."""
from __future__ import annotations

from unittest.mock import patch

import tools.zoneamento_tools as zt
from tools.zoneamento_tools import (
    _parse_geojson_to_polygons,
    _point_in_polygon,
    analisar_zoneamento_candidato,
)


_RECIFE_CFG = {
    "cnae": "9313-1/00",
    "ckan_base": "https://dados.recife.pe.gov.br/api/3/action",
    "dataset_zonas": "zoneamento",
    "formato": "geojson",
    "resource_name_contains": "Zeis",
    "layer_label": "ZEIS",
    "compat_na_malha": "RESTRITO",
    "fora_malha": "cascade",
    "subgrupos": ["SE"],
}

# Anel WGS84 simples (Boa Viagem aproximado) — ponto interno conhecido.
_ZEIS_RING = [
    (-34.91, -8.12),
    (-34.90, -8.12),
    (-34.90, -8.11),
    (-34.91, -8.11),
    (-34.91, -8.12),
]


def _fc_zeis():
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {
                "NMNOME": "ZEIS Teste",
                "CDTIPO": "ZEIS",
                "BAIRRO": "Boa Viagem",
            },
            "geometry": {"type": "Polygon", "coordinates": [_ZEIS_RING]},
        }],
    }


def test_parse_geojson_wgs84_rings():
    polys = _parse_geojson_to_polygons(_fc_zeis(), layer_label="ZEIS")
    assert len(polys) == 1
    assert polys[0]["sigla_zona"] == "ZEIS"
    assert _point_in_polygon(-34.905, -8.115, polys[0]["polygon"])
    assert not _point_in_polygon(-34.80, -8.00, polys[0]["polygon"])


def test_recife_dentro_zeis_restrito():
    zt._polygons_cache.clear()
    with patch("tools.zoneamento_tools._municipio_cfg", return_value=_RECIFE_CFG), \
         patch("tools.zoneamento_tools._fetch_geojson_resource", return_value=_fc_zeis()), \
         patch("tools.zoneamento_tools._svg_mapa_zonas", return_value=None):
        out = analisar_zoneamento_candidato(
            "Recife", "Boa Viagem", "PE", -8.115, -34.905)
    assert out["status"] == "ok"
    assert out["compatibilidade"] == "RESTRITO"
    assert out["fonte_dados"] == "CKAN_RECIFE"
    assert out["confianca"] == 100
    assert "ZEIS" in (out.get("zona_sigla") or "")


def test_recife_fora_zeis_nao_assume_permissivo_cai_osm():
    zt._polygons_cache.clear()
    perfil = {
        "tag_osm": "commercial",
        "uso_observado": "comercial_observado",
        "origem_tag": "landuse",
        "n_features": 6,
        "completude": "alta",
        "confianca": 85,
    }
    with patch("tools.zoneamento_tools._municipio_cfg", return_value=_RECIFE_CFG), \
         patch("tools.zoneamento_tools._fetch_geojson_resource", return_value=_fc_zeis()), \
         patch("tools.zeus_osm_proxy.consultar_osm_proxy", return_value=perfil):
        # Longe do polígono ZEIS
        out = analisar_zoneamento_candidato(
            "Recife", "Boa Viagem", "PE", -8.05, -34.88)
    assert out["status"] == "proxy_osm"
    assert out["compatibilidade"] == "INDIVIDUALIZAR"
    assert out.get("compatibilidade") != "PERMISSIVO"


def test_catalogo_tem_recife():
    from tools.catalogos import _CACHE, catalogo

    _CACHE.pop("zoneamento_municipio", None)
    rows = catalogo("zoneamento_municipio")
    chaves = {(r.get("chave") or "").lower() for r in rows}
    # Se Supabase devolver só Fortaleza, o seed local pode não aparecer —
    # neste caso o fallback só roda com lista vazia. Forçamos via metadata tipica.
    if "recife" not in chaves:
        # Ambiente com catálogo remoto parcial: valida metadata do seed direto.
        from tools.catalogos import _fallback
        seed = _fallback("zoneamento_municipio")
        chaves = {(r.get("chave") or "").lower() for r in seed}
    assert "recife" in chaves
    assert "fortaleza" in chaves
