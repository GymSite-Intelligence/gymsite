"""CRS ZEUS + Belo Horizonte (EPSG:31983) + Recife micro UTM."""
from __future__ import annotations

from unittest.mock import patch

import tools.zoneamento_tools as zt
from tools.zeus_crs import anel_para_wgs84, extrair_epsg, para_wgs84
from tools.zoneamento_tools import (
    _parse_geojson_to_polygons,
    _point_in_polygon,
    analisar_zoneamento_candidato,
)


def test_extrair_epsg_urn_e_codigo():
    assert extrair_epsg("urn:ogc:def:crs:EPSG::31983") == "EPSG:31983"
    assert extrair_epsg("EPSG:31985") == "EPSG:31985"
    assert extrair_epsg({"type": "name", "properties": {"name": "EPSG:4326"}}) == "EPSG:4326"


def test_bh_utm_para_wgs84_no_municipio():
    lon, lat = para_wgs84(601240.1816, 7788538.9573, "EPSG:31983")
    # BH ~ -43.9 lon, -19.9 lat
    assert -44.5 < lon < -43.0
    assert -20.5 < lat < -19.0


def test_recife_utm_25s_para_wgs84():
    lon, lat = para_wgs84(286409.3706, 9109443.6895, "EPSG:31985")
    assert -35.5 < lon < -34.5
    assert -8.5 < lat < -7.5


def test_parse_geojson_reprojeta_31983():
    # quadrado UTM em torno do ponto BH convertido
    cx, cy = 601240.0, 7788538.0
    ring = [
        (cx - 50, cy - 50),
        (cx + 50, cy - 50),
        (cx + 50, cy + 50),
        (cx - 50, cy + 50),
        (cx - 50, cy - 50),
    ]
    fc = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::31983"}},
        "features": [{
            "type": "Feature",
            "properties": {
                "SIGLA_TIPO_ZONEAMENTO": "ZEIS-1",
                "DESC_TIPO_ZONEAMENTO": "Zona Especial de Interesse Social",
            },
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        }],
    }
    polys = _parse_geojson_to_polygons(fc, layer_label="BH", crs="EPSG:31983")
    assert len(polys) == 1
    assert polys[0]["sigla_zona"] == "ZEIS-1"
    lon, lat = para_wgs84(cx, cy, "EPSG:31983")
    assert _point_in_polygon(lon, lat, polys[0]["polygon"])
    # anel já em graus
    assert abs(polys[0]["polygon"][0][0]) < 180


_BH_CFG = {
    "ckan_base": "https://ckan.pbh.gov.br/api/3/action",
    "dataset_zonas": "zoneamento-lei-11181",
    "formato": "geojson",
    "resource_name_contains": "zoneamento_11181",
    "layer_label": "ZONEAMENTO_11181",
    "crs": "EPSG:31983",
    "fora_malha": "cascade",
    "compat_default_na_malha": "CONDICIONADO",
    "compat_prefixos": {
        "ZEIS": "RESTRITO",
        "AEIS": "RESTRITO",
        "PA-": "RESTRITO",
        "OM-": "CONDICIONADO",
        "OP-": "CONDICIONADO",
    },
}


def _fc_bh_zeis():
    cx, cy = 601240.0, 7788538.0
    ring = [
        (cx - 80, cy - 80),
        (cx + 80, cy - 80),
        (cx + 80, cy + 80),
        (cx - 80, cy + 80),
        (cx - 80, cy - 80),
    ]
    return {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::31983"}},
        "features": [{
            "type": "Feature",
            "properties": {"SIGLA_TIPO_ZONEAMENTO": "ZEIS-1", "DESC_TIPO_ZONEAMENTO": "ZEIS"},
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        }],
    }


def test_bh_dentro_zeis_restrito():
    zt._polygons_cache.clear()
    lon, lat = para_wgs84(601240.0, 7788538.0, "EPSG:31983")
    with patch("tools.zoneamento_tools._municipio_cfg", return_value=_BH_CFG), \
         patch("tools.zoneamento_tools._fetch_geojson_resource", return_value=_fc_bh_zeis()), \
         patch("tools.zoneamento_tools._svg_mapa_zonas", return_value=None), \
         patch("tools.zoneamento_tools._png_mapa_zonas", return_value=None):
        out = analisar_zoneamento_candidato(
            "Belo Horizonte", "Centro", "MG", lat, lon)
    assert out["status"] == "ok"
    assert out["compatibilidade"] == "RESTRITO"
    assert out["fonte_dados"] == "CKAN_BELO HORIZONTE"
    assert "ZEIS" in (out.get("zona_sigla") or "")


def test_bh_fora_cascade_osm_nao_permissivo():
    zt._polygons_cache.clear()
    perfil = {
        "tag_osm": "residential",
        "uso_observado": "residencial_observado",
        "n_features": 4,
        "completude": "alta",
        "confianca": 85,
        "origem_tag": "landuse",
    }
    with patch("tools.zoneamento_tools._municipio_cfg", return_value=_BH_CFG), \
         patch("tools.zoneamento_tools._fetch_geojson_resource", return_value=_fc_bh_zeis()), \
         patch("tools.zeus_osm_proxy.consultar_osm_proxy", return_value=perfil):
        out = analisar_zoneamento_candidato(
            "BH", "Pampulha", "MG", -19.85, -43.98)
    assert out["status"] == "proxy_osm"
    assert out["compatibilidade"] == "INDIVIDUALIZAR"


def test_municipio_cfg_sinonimo_bh():
    from tools.catalogos import _CACHE, _fallback

    _CACHE.pop("zoneamento_municipio", None)
    # Usa seed local se remoto não tiver BH
    with patch("tools.catalogos.catalogo", side_effect=lambda n: _fallback(n)):
        cfg = zt._municipio_cfg("Belo Horizonte")
        cfg2 = zt._municipio_cfg("BH")
    assert cfg and cfg.get("crs") == "EPSG:31983"
    assert cfg2 and cfg2.get("dataset_zonas") == "zoneamento-lei-11181"


def test_anel_para_wgs84_noop_4326():
    ring = [(-43.9, -19.9), (-43.8, -19.9), (-43.8, -19.8)]
    out = anel_para_wgs84(ring, "EPSG:4326")
    assert out[0][0] == -43.9
