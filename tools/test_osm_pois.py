"""VEC-378 Fase 2 — osm_pois (Overpass mockado)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from tools.osm_pois import (
    osm_pois,
    polos_para_ancoragem,
    resumo_ancoras_ondeabrir,
)


def _fake_overpass_payload() -> dict:
    return {
        "elements": [
            {
                "type": "node",
                "id": 1,
                "lat": -3.7280,
                "lon": -38.4895,
                "tags": {"amenity": "parking", "name": "Estacionamento X"},
            },
            {
                "type": "node",
                "id": 2,
                "lat": -3.7275,
                "lon": -38.4900,
                "tags": {"amenity": "school", "name": "Escola Y"},
            },
            {
                "type": "node",
                "id": 3,
                "lat": -3.7270,
                "lon": -38.4885,
                "tags": {"shop": "supermarket", "name": "Mercado Z"},
            },
            {
                "type": "node",
                "id": 4,
                "lat": -3.7265,
                "lon": -38.4890,
                "tags": {"amenity": "bus_station", "name": "Terminal W"},
            },
        ]
    }


def test_osm_pois_classifica_e_conta():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = _fake_overpass_payload()

    with patch("httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.post.return_value = mock_resp
        out = osm_pois(-3.7278, -38.4895, raio_m=1000, use_cache=False)

    assert out["status"] == "ok"
    assert out["n_pois"] >= 3
    assert out["contagens"].get("parking", 0) >= 1
    assert out["contagens"].get("school", 0) >= 1
    assert out["fonte"] == "overpass_osm"
    assert "OpenStreetMap" in (out.get("carimbo") or "")
    assert all("distancia_m" in p for p in out["pois"])


def test_polos_para_ancoragem_ignora_parking():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = _fake_overpass_payload()

    with patch("httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.post.return_value = mock_resp
        with patch("tools.osm_pois._cache_get", return_value=None):
            polos = polos_para_ancoragem(-3.7278, -38.4895, raio_m=1000)

    assert polos
    assert all(p.get("tipo_polo") != "estacionamento" for p in polos)
    assert any(p.get("tipo_polo") == "terminal_transporte" for p in polos)


def test_resumo_ondeabrir_campos():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = _fake_overpass_payload()

    with patch("httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.post.return_value = mock_resp
        with patch("tools.osm_pois._cache_get", return_value=None):
            r = resumo_ancoras_ondeabrir(-3.7278, -38.4895, raio_m=1000)

    assert r["estacionamentos_n"] >= 1
    assert r["escolas_n"] >= 1
    assert r["transporte_n"] >= 1
    assert r["ancoras_top"]


def test_fail_soft_http_erro():
    mock_resp = MagicMock()
    mock_resp.status_code = 504

    with patch("httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value.post.return_value = mock_resp
        out = osm_pois(-3.7, -38.5, use_cache=False)

    assert out["status"] == "indisponivel"
    assert out["pois"] == []


def test_space_syntax_fetch_usa_osm_pois():
    from tools.space_syntax import fetch_pois_from_overpass

    fake = {
        "status": "ok",
        "pois": [
            {
                "nome": "Escola Y",
                "categoria": "school",
                "lat": -3.7275,
                "lng": -38.49,
                "distancia_m": 80,
                "fonte": "overpass_osm",
            }
        ],
    }
    with patch("tools.osm_pois.osm_pois", return_value=fake):
        pois = fetch_pois_from_overpass(-3.7278, -38.49, radius=1000)
    assert len(pois) == 1
    assert pois[0]["name"] == "Escola Y"
    assert pois[0]["category"] == "school"
    assert "weight" in pois[0]
