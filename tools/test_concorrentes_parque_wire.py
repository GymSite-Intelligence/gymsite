"""Testes — wire registro-primeiro: parque CNPJ vira base, Places enriquece. Sem rede."""
from __future__ import annotations

import tools.competitor_tools as ct


_PARQUE = {
    "status": "ok",
    "concorrentes": [
        {"cnpj": "1", "nome": "Smart Fit Cocó", "endereco": "Av X 100", "telefone": "8530000000"},
        {"cnpj": "2", "nome": "Studio Sem Places", "endereco": "Rua Y", "telefone": "8540000000"},
    ],
}

_PLACE = {
    "id": "ChIJ_abc",
    "displayName": {"text": "Smart Fit - Cocó"},
    "formattedAddress": "Av X, 100 - Cocó, Fortaleza - CE",
    "location": {"latitude": -3.74, "longitude": -38.49},
    "rating": 4.3,
    "userRatingCount": 1200,
    "businessStatus": "OPERATIONAL",
    "types": ["gym"],
    "nationalPhoneNumber": "(85) 3000-0000",
    "websiteUri": "http://smartfit.com",
    "googleMapsUri": "http://maps/abc",
    "regularOpeningHours": {"weekdayDescriptions": ["Segunda: 24 horas"]},
}


def _setup(monkeypatch):
    import tools.concorrentes_parque_tools as cp
    monkeypatch.setattr(cp, "listar_concorrentes_parque", lambda c, u, b: dict(_PARQUE))
    # Places casa só quem tem "Smart" no nome
    monkeypatch.setattr(
        ct, "_places_match_por_texto",
        lambda nome, end, cid, uf: _PLACE if "smart" in nome.lower() else None,
    )


def test_match_places_usa_place_id_e_rating_reais(monkeypatch):
    _setup(monkeypatch)
    out, _ = ct._concorrentes_parque_enriquecidos("Cocó", "Fortaleza", "CE", -3.74, -38.49)
    assert len(out) == 2
    a = next(c for c in out if c["cnpj"] == "1")
    assert a["place_id"] == "ChIJ_abc"           # place_id real (não cnpj/)
    assert a["rating"] == 4.3 and a["num_avaliacoes"] == 1200
    assert a["tem_24h"] is True                  # "24 horas" no horário
    assert a["fonte_busca"] == "cnpj_parque+places"


def test_sem_match_lista_mesmo_assim_sem_reviews(monkeypatch):
    _setup(monkeypatch)
    out, _ = ct._concorrentes_parque_enriquecidos("Cocó", "Fortaleza", "CE", -3.74, -38.49)
    b = next(c for c in out if c["cnpj"] == "2")
    assert b["place_id"] == "cnpj/2"             # fallback CNPJ (sem Places)
    assert b["rating"] is None
    assert b["fonte_busca"] == "cnpj_parque_sem_places"
    assert b["telefone"] == "8540000000"         # mantém telefone do parque


def test_parque_vazio_devolve_lista_vazia(monkeypatch):
    import tools.concorrentes_parque_tools as cp
    monkeypatch.setattr(cp, "listar_concorrentes_parque",
                        lambda c, u, b: {"status": "ok", "concorrentes": []})
    out, _ = ct._concorrentes_parque_enriquecidos("X", "Y", "ZZ", 0.0, 0.0)
    assert out == []                              # → buscar_academias cai no fallback 3km
