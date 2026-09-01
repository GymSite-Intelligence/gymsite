"""top_vias_por_fluxo — agregação por via a partir do geojson do motor angular."""
from __future__ import annotations

import tools.fluxo_pedestre_tools as ft


def test_classificar_tipo_via():
    assert ft._classificar_tipo_via("Avenida Beira Mar") == "avenida"
    assert ft._classificar_tipo_via("Rua Engenheiro Samir Hiluy") == "rua"
    assert ft._classificar_tipo_via("Travessa X") == "travessa"


def test_normalize_street_name_lista():
    assert (
        ft._normalize_street_name(["Rua Ligia Monte", "Avenida Sebastião de Abreu"])
        == "Avenida Sebastião de Abreu"
    )
    assert ft._normalize_street_name("['Rua A', 'Avenida B']") == "Avenida B"
    assert ft._normalize_street_name("Avenida Saboia") == "Avenida Saboia"


def test_agregar_features_por_via_media():
    features = [
        {"properties": {"street_name": "Av A", "flow_score": 1.0, "length_meters": 100}},
        {"properties": {"street_name": "Av A", "flow_score": 0.5, "length_meters": 100}},
        {"properties": {"street_name": "Rua B", "flow_score": 0.2, "length_meters": 50}},
        {"properties": {"street_name": "", "flow_score": 0.9, "length_meters": 10}},
    ]
    vias = ft._agregar_features_por_via(features)
    assert set(vias) == {"Av A", "Rua B"}
    assert vias["Av A"]["n_segments"] == 2
    assert vias["Av A"]["score_medio"] == 0.75
    assert vias["Av A"]["score_max"] == 1.0
    assert vias["Av A"]["tipo_via"] == "avenida"


def test_agregar_lista_e_rank_por_max():
    features = [
        {
            "properties": {
                "street_name": ["Rua Ligia Monte", "Avenida Sebastião de Abreu"],
                "flow_score": 0.68,
                "length_meters": 200,
            }
        },
        {
            "properties": {
                "street_name": "Avenida Almirante Henrique Saboia",
                "flow_score": 1.0,
                "length_meters": 500,
            }
        },
        {
            "properties": {
                "street_name": "Avenida Almirante Henrique Saboia",
                "flow_score": 0.3,
                "length_meters": 400,
            }
        },
        {
            "properties": {
                "street_name": "Trilha do Cocó",
                "flow_score": 0.99,
                "length_meters": 100,
            }
        },
    ]
    vias = ft._agregar_features_por_via(features)
    assert "Trilha do Cocó" not in vias
    assert "Avenida Sebastião de Abreu" in vias
    assert "[" not in "".join(vias.keys())
    ranked = sorted(vias.items(), key=lambda kv: kv[1]["score_rank"], reverse=True)
    assert ranked[0][0] == "Avenida Almirante Henrique Saboia"
    assert ranked[0][1]["score_rank"] == 1.0


def test_top_vias_por_fluxo_agrega_e_ordena(monkeypatch):
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "street_name": "Avenida Almirante Henrique Saboia",
                    "flow_score": 1.0,
                    "length_meters": 500,
                },
            },
            {
                "type": "Feature",
                "properties": {
                    "street_name": "Avenida Almirante Henrique Saboia",
                    "flow_score": 0.9,
                    "length_meters": 400,
                },
            },
            {
                "type": "Feature",
                "properties": {
                    "street_name": "Rua Engenheiro Samir Hiluy",
                    "flow_score": 0.26,
                    "length_meters": 200,
                },
            },
        ],
    }

    monkeypatch.setattr(
        ft,
        "run_flow_analysis",
        lambda *a, **k: {
            "success": True,
            "confianca": "alta",
            "geojson": geojson,
            "statistics": {"total_segments": 120, "mean_flow_score": 0.5},
            "top_segments": [],
        },
    )

    out = ft.top_vias_por_fluxo(-3.74, -38.48, top_n=3, bairro="Coco")
    assert out["status"] == "ok"
    assert out["confianca"] == "alta"
    assert out["top_vias"][0]["nome_via"] == "Avenida Almirante Henrique Saboia"
    assert out["top_vias"][0]["fluxo_score"] >= 90
    assert out["top_vias"][1]["nome_via"] == "Rua Engenheiro Samir Hiluy"


def test_top_vias_fail_soft(monkeypatch):
    monkeypatch.setattr(
        ft,
        "run_flow_analysis",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    out = ft.top_vias_por_fluxo(-3.74, -38.48)
    assert out["status"] == "indisponivel"
    assert out["top_vias"] == []
