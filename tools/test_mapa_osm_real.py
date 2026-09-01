"""Mapas OSM raster — projeção + overlay (tiles mockados, sem rede)."""
from __future__ import annotations

import io
from unittest.mock import patch

from PIL import Image

from tools.mapa_osm_real import (
    calcular_zoom_otimo,
    cor_fluxo,
    gerar_mapa_top_vias,
    gerar_mapa_zoneamento,
    latlon_to_world_px,
    png_to_data_uri,
    try_mapa_vias_data_uri,
)


def _fake_tile_png(color=(200, 210, 220)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (256, 256), color).save(buf, format="PNG")
    return buf.getvalue()


def test_mercator_monotonic_east_south():
    z = 15
    x0, y0 = latlon_to_world_px(-3.75, -38.50, z)
    x1, y1 = latlon_to_world_px(-3.75, -38.40, z)  # leste
    x2, y2 = latlon_to_world_px(-3.80, -38.50, z)  # sul
    assert x1 > x0
    assert y2 > y0


def test_zoom_otimo_cabe_no_viewport():
    # ~1 km em Meireles
    bounds = (-3.732, -38.495, -3.722, -38.485)
    z = calcular_zoom_otimo(bounds, 560, 300)
    assert 12 <= z <= 17


def test_cor_fluxo_extremos():
    assert cor_fluxo(0).lower() == "#94a3b8"
    assert cor_fluxo(100).startswith("#")


def test_gerar_mapa_vias_com_tiles_mock():
    vias = [
        {
            "nome_via": "Av Beira Mar",
            "fluxo_score": 100,
            "segments": [[
                [-38.490, -3.728],
                [-38.488, -3.727],
                [-38.486, -3.726],
            ]],
        },
        {
            "nome_via": "Rua Lateral",
            "fluxo_score": 30,
            "segments": [[
                [-38.491, -3.729],
                [-38.4895, -3.7285],
                [-38.488, -3.728],
            ]],
        },
    ]
    with patch("tools.mapa_osm_real._buscar_tile", return_value=_fake_tile_png()):
        png = gerar_mapa_top_vias(vias, (-3.7278, -38.489))
    assert png and png[:8] == b"\x89PNG\r\n\x1a\n"
    img = Image.open(io.BytesIO(png))
    assert img.size == (560, 300)


def test_split_nao_liga_trechos_distantes():
    from tools.mapa_osm_real import _split_saltos

    # Dois trechos ~500m aparte (não devem virar um path só)
    pts = [
        (-3.728, -38.490),
        (-3.728, -38.489),
        (-3.720, -38.480),  # salto grande
        (-3.720, -38.479),
    ]
    segs = _split_saltos(pts, max_salto_m=380)
    assert len(segs) == 2


def test_gerar_mapa_zonas_com_tiles_mock():
    zonas = [
        {
            "sigla_zona": "ZEDUS",
            "polygon": [
                (-38.492, -3.730),
                (-38.486, -3.730),
                (-38.486, -3.725),
                (-38.492, -3.725),
                (-38.492, -3.730),
            ],
        }
    ]
    with patch("tools.mapa_osm_real._buscar_tile", return_value=_fake_tile_png((220, 230, 240))):
        png = gerar_mapa_zoneamento(zonas, (-3.7278, -38.489))
    assert png and png[:8] == b"\x89PNG\r\n\x1a\n"


def test_fail_soft_sem_coords():
    assert gerar_mapa_top_vias([{"nome_via": "X", "fluxo_score": 50}], (-3.7, -38.5)) is None
    assert gerar_mapa_zoneamento([], (-3.7, -38.5)) is None


def test_data_uri_e_try_vias():
    vias = [
        {
            "nome_via": "Av A",
            "fluxo_score": 80,
            "coords": [[-38.49, -3.728], [-38.488, -3.727]],
        }
    ]
    with patch("tools.mapa_osm_real._buscar_tile", return_value=_fake_tile_png()):
        uri = try_mapa_vias_data_uri(vias, -3.728, -38.489)
    assert uri and uri.startswith("data:image/png;base64,")
    assert png_to_data_uri(b"\x89PNG") == "data:image/png;base64,iVBORw=="
