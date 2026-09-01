from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(
        "backend.routers.carto._user_id_from_request",
        lambda request: "user-test",
    )
    from backend.routers.carto import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_hex_count_401_without_user(monkeypatch):
    monkeypatch.setattr(
        "backend.routers.carto._user_id_from_request",
        lambda request: None,
    )
    from backend.routers.carto import router

    app = FastAPI()
    app.include_router(router)
    r = TestClient(app).get("/api/carto/hex-count", params={"lat": -3.7455, "lng": -38.4855})
    assert r.status_code == 401
    assert "n_academias" not in r.json()


def test_hex_count_200(client):
    r = client.get("/api/carto/hex-count", params={"lat": -3.7455, "lng": -38.4855})
    assert r.status_code == 200
    body = r.json()
    assert body["n_academias"] >= 1
    assert body["base"] == "H3 res 8 da tabela gym_hex_cidade"


def test_hex_count_404_no_n_field(client):
    r = client.get("/api/carto/hex-count", params={"lat": 0, "lng": 0})
    assert r.status_code == 404
    assert "n_academias" not in r.json()


def test_hex_count_post_200(client):
    r = client.post("/api/carto/hex-count", json={"lat": -3.7455, "lng": -38.4855})
    assert r.status_code == 200
    body = r.json()
    assert body["n_academias"] >= 1
    assert "n_academias" in body


def test_hex_count_post_401_without_user(monkeypatch):
    monkeypatch.setattr(
        "backend.routers.carto._user_id_from_request",
        lambda request: None,
    )
    from backend.routers.carto import router

    app = FastAPI()
    app.include_router(router)
    r = TestClient(app).post(
        "/api/carto/hex-count",
        json={"lat": -3.7455, "lng": -38.4855},
    )
    assert r.status_code == 401
    assert "n_academias" not in r.json()
