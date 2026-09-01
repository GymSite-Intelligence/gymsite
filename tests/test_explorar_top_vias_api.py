"""POST /api/explorar/top-vias — top vias por fluxo pedestre."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from backend.routers.explorar import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_top_vias_ok_shape(client, monkeypatch):
    def fake(lat, lng, **kwargs):
        return {
            "status": "ok",
            "top_vias": [
                {
                    "nome_via": "Rua X",
                    "fluxo_score": 80,
                    "coords": [[-38.4, -3.7], [-38.41, -3.71]],
                }
            ],
            "confianca": "alta",
            "mapa_png": "SHOULD_STRIP",
        }

    monkeypatch.setattr("tools.fluxo_pedestre_tools.top_vias_por_fluxo", fake)
    r = client.post("/api/explorar/top-vias", json={"lat": -3.74, "lng": -38.48})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "mapa_png" not in body
    assert body["top_vias"][0]["nome_via"] == "Rua X"


def test_top_vias_fail_soft(client, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("osmnx down")

    monkeypatch.setattr("tools.fluxo_pedestre_tools.top_vias_por_fluxo", boom)
    r = client.post("/api/explorar/top-vias", json={"lat": -3.74, "lng": -38.48})
    assert r.status_code == 200
    assert r.json()["status"] == "indisponivel"
    assert r.json()["top_vias"] == []
