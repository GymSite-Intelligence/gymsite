"""POST /api/explorar/analisar — Turnstile + entitlement + shape Absorção."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

BODY = {
    "lat": -3.745,
    "lng": -38.485,
    "lente": "1km",
    "cidade": "Fortaleza",
    "bairro": "Cocó",
    "uf": "CE",
    "email": "lead@example.com",
}


@pytest.fixture
def client():
    from backend.routers.explorar import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_capturar_lead_explorar_agenda_resend(monkeypatch):
    from backend.routers import explorar as exp

    enrolled = {}

    class _Sb:
        pass

    monkeypatch.setattr("backend.routers.site_agent._sb", lambda: _Sb())
    monkeypatch.setattr(
        "backend.routers.leads._persistir_lead",
        lambda _sb, data: {"id": "lead-bessa", "fonte": data.fonte, "email": str(data.email)},
    )
    monkeypatch.setattr(
        "tools.resend_client.enroll_explorar_lead",
        lambda email, cidade, bairro, resumo=None: enrolled.update(
            email=email, cidade=cidade, bairro=bairro, resumo=resumo
        ),
    )
    exp._capturar_lead_explorar("teste@gymsite.com.br", "João Pessoa", "Bessa")
    assert enrolled["email"] == "teste@gymsite.com.br"
    assert enrolled["cidade"] == "João Pessoa"
    assert enrolled["bairro"] == "Bessa"


def test_anon_without_turnstile_403(client, monkeypatch):
    async def _deny(*_a, **_k):
        return False

    monkeypatch.setattr("backend.routers.explorar.verificar_turnstile", _deny)
    monkeypatch.setattr("backend.routers.explorar._user_id_from_request", lambda *_a, **_k: None)
    r = client.post("/api/explorar/analisar", json=BODY)
    assert r.status_code == 403


def test_anon_cap_estourado_fila(client, monkeypatch):
    async def _ok(*_a, **_k):
        return True

    monkeypatch.setattr("backend.routers.explorar.verificar_turnstile", _ok)
    monkeypatch.setattr("backend.routers.explorar._user_id_from_request", lambda *_a, **_k: None)
    monkeypatch.setattr("backend.routers.explorar._email_ja_usou_explorar", lambda *_a, **_k: False)
    monkeypatch.setattr("backend.routers.explorar._cap_explorar_estourado", lambda *_a, **_k: True)
    monkeypatch.setattr("backend.routers.explorar._capturar_lead_explorar", lambda *_a, **_k: None)
    r = client.post(
        "/api/explorar/analisar",
        json={**BODY, "turnstile_token": "ok"},
    )
    assert r.status_code == 200
    assert r.json().get("status") == "fila"


def test_anon_email_already_used_quota(client, monkeypatch):
    async def _ok(*_a, **_k):
        return True

    captured = {}

    monkeypatch.setattr("backend.routers.explorar.verificar_turnstile", _ok)
    monkeypatch.setattr("backend.routers.explorar._user_id_from_request", lambda *_a, **_k: None)
    monkeypatch.setattr("backend.routers.explorar._email_ja_usou_explorar", lambda *_a, **_k: True)
    monkeypatch.setattr(
        "backend.routers.explorar._capturar_lead_explorar",
        lambda email, cidade, bairro, *_a, **_k: captured.update(
            email=email, cidade=cidade, bairro=bairro
        ),
    )
    r = client.post(
        "/api/explorar/analisar",
        json={**BODY, "turnstile_token": "ok"},
    )
    assert r.status_code == 200
    assert r.json().get("status") == "quota_used"
    assert "crie sua conta" not in r.json().get("mensagem", "").lower()
    assert captured["email"] == "lead@example.com"


def test_authenticated_returns_absorcao_rotulo(client, monkeypatch):
    monkeypatch.setattr(
        "backend.routers.explorar._user_id_from_request",
        lambda *_a, **_k: "user-1",
    )
    monkeypatch.setattr(
        "backend.routers.explorar.run_explorar_analise",
        lambda **_k: {
            "lente": "1km",
            "base_espacial_label": "raio 1 km · centróide pin · IBGE Censo 2022",
            "pin": {"lat": -3.745, "lng": -38.485},
            "concorrentes": [],
            "absorcao_margem_fresca": {"rotulo": "roubo"},
            "carimbo_base": "0 academias · raio 1 km · SearchAPI Maps · n/a",
        },
    )
    r = client.post(
        "/api/explorar/analisar",
        json={"lat": -3.745, "lng": -38.485, "lente": "1km"},
        headers={"Authorization": "Bearer fake"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") != "quota_used"
    assert data["absorcao_margem_fresca"]["rotulo"] in ("fresco", "misto", "roubo")
    assert "score" not in data
    assert "oportunidade clara" not in str(data).lower()


def test_authenticated_passa_tipo_negocio(client, monkeypatch):
    seen: dict = {}

    def _run(**kwargs):
        seen.update(kwargs)
        return {
            "lente": "1km",
            "tipo_negocio": kwargs.get("tipo_negocio") or "academia",
            "base_espacial_label": "raio 1 km",
            "pin": {"lat": -3.745, "lng": -38.485},
            "concorrentes": [],
            "absorcao_margem_fresca": {"rotulo": "fresco"},
            "carimbo_base": "0 · raio 1 km · SearchAPI Maps · n/a",
        }

    monkeypatch.setattr(
        "backend.routers.explorar._user_id_from_request",
        lambda *_a, **_k: "user-1",
    )
    monkeypatch.setattr("backend.routers.explorar.run_explorar_analise", _run)
    r = client.post(
        "/api/explorar/analisar",
        json={
            "lat": -3.745,
            "lng": -38.485,
            "lente": "1km",
            "tipo_negocio": "crossfit_box",
        },
        headers={"Authorization": "Bearer fake"},
    )
    assert r.status_code == 200
    assert seen.get("tipo_negocio") == "crossfit_box"
    assert r.json()["tipo_negocio"] == "crossfit_box"


def test_authenticated_passa_publico_e_area(client, monkeypatch):
    seen: dict = {}

    def _run(**kwargs):
        seen.update(kwargs)
        return {
            "lente": "1km",
            "tipo_negocio": "academia",
            "base_espacial_label": "raio 1 km",
            "pin": {"lat": -3.745, "lng": -38.485},
            "concorrentes": [],
            "absorcao_margem_fresca": {"rotulo": "fresco", "faixas_primario": ["25-39"]},
            "carimbo_base": "0 · raio 1 km · SearchAPI Maps · n/a",
        }

    monkeypatch.setattr(
        "backend.routers.explorar._user_id_from_request",
        lambda *_a, **_k: "user-1",
    )
    monkeypatch.setattr("backend.routers.explorar.run_explorar_analise", _run)
    r = client.post(
        "/api/explorar/analisar",
        json={
            "lat": -3.745,
            "lng": -38.485,
            "lente": "1km",
            "publico_alvo": "25-39",
            "area_m2": 1150,
            "idade_min": 25,
            "idade_max": 39,
        },
        headers={"Authorization": "Bearer fake"},
    )
    assert r.status_code == 200
    assert seen.get("publico_alvo") == "25-39"
    assert seen.get("area_candidato_m2") == 1150
    assert seen.get("idade_min") == 25
    assert seen.get("idade_max") == 39


def test_authenticated_passa_cidade_bairro_endereco(client, monkeypatch):
    seen: dict = {}

    def _run(**kwargs):
        seen.update(kwargs)
        return {
            "lente": "1km",
            "tipo_negocio": "academia",
            "base_espacial_label": "raio 1 km",
            "pin": {"lat": -3.745, "lng": -38.485},
            "concorrentes": [{"nome": "Uniq", "lat": -3.745, "lng": -38.482}],
            "absorcao_margem_fresca": {"rotulo": "fresco"},
            "carimbo_base": "1 · raio 1 km · SearchAPI Maps · academia",
        }

    monkeypatch.setattr(
        "backend.routers.explorar._user_id_from_request",
        lambda *_a, **_k: "user-1",
    )
    monkeypatch.setattr("backend.routers.explorar.run_explorar_analise", _run)
    r = client.post(
        "/api/explorar/analisar",
        json={
            "lat": -3.745,
            "lng": -38.485,
            "lente": "1km",
            "cidade": "Fortaleza",
            "bairro": "Cocó",
            "uf": "CE",
            "endereco": "Cocó, Fortaleza, CE",
        },
        headers={"Authorization": "Bearer fake"},
    )
    assert r.status_code == 200
    assert seen.get("cidade") == "Fortaleza"
    assert seen.get("bairro") == "Cocó"
    assert seen.get("endereco") == "Cocó, Fortaleza, CE"
    assert len(r.json()["concorrentes"]) == 1


def test_autocomplete_usa_nominatim_sem_places(client, monkeypatch):
    called = {"places": 0}

    def _places(**_k):
        called["places"] += 1
        return {"suggestions": [{"placeId": "ChIJ", "bairro": "Fake"}]}

    monkeypatch.setattr("tools.places_autocomplete.places_autocomplete", _places)
    monkeypatch.setattr(
        "backend.routers.explorar.suggest_nominatim",
        lambda *_a, **_k: [
            {
                "placeId": "osm:1",
                "bairro": "Cocó",
                "contexto": "Fortaleza, CE",
                "textoCompleto": "Cocó, Fortaleza - CE",
                "lat": -3.7455,
                "lng": -38.4855,
                "osm_class": "boundary",
                "osm_type_tag": "administrative",
            }
        ],
    )
    r = client.post(
        "/api/explorar/autocomplete",
        json={"q": "Cocó", "lat": -3.74, "lng": -38.48},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["fonte"] == "nominatim"
    assert data["suggestions"][0]["bairro"] == "Cocó"
    assert data["suggestions"][0]["lat"] == -3.7455
    assert called["places"] == 0


def test_autocomplete_bessa_sem_bias_fortaleza(client, monkeypatch):
    def _suggest(q, lat=None, lng=None, **_k):
        if lat is not None:
            return []
        return [
            {
                "placeId": "osm_rel_bessa",
                "bairro": "Bessa",
                "contexto": "João Pessoa, PB",
                "textoCompleto": "Bessa, João Pessoa - PB",
                "lat": -7.078,
                "lng": -34.833,
                "osm_class": "place",
                "osm_type_tag": "suburb",
            }
        ]

    monkeypatch.setattr("backend.routers.explorar.suggest_nominatim", _suggest)
    r = client.post("/api/explorar/autocomplete", json={"q": "Bessa"})
    assert r.status_code == 200
    data = r.json()
    assert data["fonte"] == "nominatim"
    assert data["suggestions"][0]["bairro"] == "Bessa"


def test_geocode_pirapora_minas_gerais_devolve_uf(client, monkeypatch):
    monkeypatch.setattr("tools.explorar_pin.resolver_explorar_pin", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "tools.maps_fallback.geocode_nominatim",
        lambda *_a, **_k: {
            "lat": -17.347,
            "lng": -44.942,
            "fonte_geocode": "nominatim",
        },
    )
    r = client.post(
        "/api/explorar/geocode",
        json={"endereco": "Centro, Pirapora, Minas Gerais, Região Sudeste, Brasil"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["bairro"] == "Centro"
    assert data["cidade"] == "Pirapora"
    assert data["uf"] == "MG"


def test_bearer_invalido_401_nao_pede_turnstile(client, monkeypatch):
    monkeypatch.setattr("backend.routers.explorar._user_id_from_request", lambda *_a, **_k: None)
    r = client.post(
        "/api/explorar/analisar",
        json={"lat": -3.745, "lng": -38.485, "lente": "1km"},
        headers={"Authorization": "Bearer expired"},
    )
    assert r.status_code == 401
    detail = r.json().get("detail") or ""
    assert "sessão" in detail.lower() or "sessao" in detail.lower()


def test_geocode_rua_usa_nominatim(client, monkeypatch):
    monkeypatch.setattr("tools.explorar_pin.resolver_explorar_pin", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "tools.maps_fallback.geocode_nominatim",
        lambda *_a, **_k: {
            "lat": -3.731,
            "lng": -38.522,
            "fonte_geocode": "nominatim",
            "formatted_address": "Rua Silva Paulet, Meireles, Fortaleza",
        },
    )
    r = client.post(
        "/api/explorar/geocode",
        json={"endereco": "Rua Silva Paulet, Meireles, Fortaleza, CE"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["fonte"] == "nominatim"
    assert data["lat"] == -3.731
    assert data["lng"] == -38.522


def test_geocode_coco_usa_centroide_ibge(client):
    r = client.post(
        "/api/explorar/geocode",
        json={"endereco": "Cocó, Fortaleza, Ceará, Brasil"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["fonte"] == "ibge_bairro_centroide"
    assert data["bairro"] == "Cocó"
    assert data["cidade"] == "Fortaleza"
    assert data["uf"] == "CE"
    assert -3.76 <= data["lat"] <= -3.73
    assert -38.51 <= data["lng"] <= -38.46


def test_isocronas_retorna_aneis(client, monkeypatch):
    monkeypatch.setattr(
        "tools.osm_isocronas.fetch_isocronas",
        lambda *_a, **_k: {
            "m5": [[-3.74, -38.48]],
            "m10": [[-3.74, -38.49]],
            "m15": [[-3.74, -38.50]],
            "fonte": "valhalla",
        },
    )
    r = client.post(
        "/api/explorar/isocronas",
        json={"lat": -3.745, "lng": -38.485, "modo": "pe"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["fonte"] == "valhalla"
    assert len(data["m5"]) >= 1
    assert len(data["m15"]) >= 1
