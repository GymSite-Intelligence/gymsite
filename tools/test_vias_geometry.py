"""Geometria + SVG das top vias (OSM via GeoJSON do motor)."""
from __future__ import annotations

from tools.vias_geometry_tools import (
    anexar_geometria_e_mapa,
    expor_geometria_vias,
    render_mapa_vias_svg,
)


def _feat(nome: str, coords: list[list[float]], flow: float) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coords},
        "properties": {"street_name": nome, "flow_score": flow, "length_meters": 100},
    }


def test_expor_geometria_casa_por_nome():
    features = [
        _feat("Avenida Saboia", [[-38.48, -3.75], [-38.479, -3.749], [-38.478, -3.748]], 1.0),
        _feat("Avenida Saboia", [[-38.478, -3.748], [-38.477, -3.747]], 0.9),
        _feat("Rua Lateral", [[-38.481, -3.751], [-38.480, -3.750]], 0.3),
    ]
    top = [
        {"nome_via": "Avenida Saboia", "fluxo_score": 100, "concorrentes_no_trecho": 0},
        {"nome_via": "Rua Lateral", "fluxo_score": 30, "concorrentes_no_trecho": 1},
    ]
    out = expor_geometria_vias(features, top)
    assert out["status"] == "ok"
    assert out["n_com_geometria"] == 2
    assert len(out["geometrias"]["Avenida Saboia"]["coords"]) >= 3


def test_render_svg_contem_path_e_ponto():
    geos = {
        "Avenida Saboia": {
            "coords": [[-38.48, -3.75], [-38.479, -3.749], [-38.478, -3.748]],
            "fluxo_score": 100,
        },
        "Rua Lateral": {
            "coords": [[-38.481, -3.751], [-38.4805, -3.7505]],
            "fluxo_score": 40,
        },
    }
    svg = render_mapa_vias_svg(geos, -3.75, -38.48)
    assert svg and svg.startswith("<svg")
    assert "<path " in svg
    assert "<circle " in svg
    assert "#DC2626" in svg  # fluxo 100


def test_anexar_muta_top_vias():
    features = [
        _feat("Av A", [[-38.48, -3.75], [-38.479, -3.749]], 1.0),
    ]
    top = [{"nome_via": "Av A", "fluxo_score": 100}]
    svg = anexar_geometria_e_mapa(top, features, -3.75, -38.48)
    assert svg and "<svg" in svg
    assert top[0].get("coords")
    assert len(top[0]["coords"]) >= 2


def test_fail_soft_sem_features():
    out = expor_geometria_vias([], [{"nome_via": "X", "fluxo_score": 50}])
    assert out["status"] == "indisponivel"
    assert render_mapa_vias_svg({}, -3.75, -38.48) is None
