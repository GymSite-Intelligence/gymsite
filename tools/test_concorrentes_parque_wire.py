"""Testes — âncora bairro (textSearch + filtro fitness/bairro + cross parque). Sem rede."""
from __future__ import annotations

import tools.competitor_tools as ct


def _place(nome, end, tipos, rating=4.5, aval=50):
    return {
        "id": "pid_" + nome.replace(" ", ""),
        "displayName": {"text": nome},
        "formattedAddress": end,
        "location": {"latitude": -3.74, "longitude": -38.49},
        "rating": rating, "userRatingCount": aval,
        "types": tipos, "businessStatus": "OPERATIONAL",
        "regularOpeningHours": {"weekdayDescriptions": ["Segunda: 24 horas"]},
        "nationalPhoneNumber": "(85) 3000-0000",
    }


_PLACES = [
    _place("Parque Esportes", "R. X - Cocó, Fortaleza - CE", ["gym", "sports_activity_location"]),
    _place("Vistta Rooftop Restaurante", "Av Y - Cocó, Fortaleza - CE", ["restaurant"]),          # type fora
    _place("Duets Office Towers", "Av Z - Cocó, Fortaleza - CE", ["corporate_office"]),            # type fora
    _place("Gaviões 24h", "R. W - Aldeota, Fortaleza - CE", ["gym", "fitness_center"]),            # bairro fora
    _place("CT Greenlife", "R. V - Cocó, Fortaleza - CE", ["fitness_center", "gym"]),
]


def _setup(monkeypatch, parque=None):
    monkeypatch.setattr(ct, "_places_textsearch", lambda q, **k: list(_PLACES))
    import tools.concorrentes_parque_tools as cp
    monkeypatch.setattr(
        cp, "listar_concorrentes_parque",
        lambda c, u, b: parque or {"status": "ok", "concorrentes": []},
    )


def test_filtra_tipo_e_bairro(monkeypatch):
    _setup(monkeypatch)
    out = ct._descobrir_concorrentes_bairro("academia", "Cocó", "Fortaleza", "CE", -3.74, -38.49)
    nomes = {o["nome"] for o in out}
    assert nomes == {"Parque Esportes", "CT Greenlife"}      # só fitness + Cocó
    assert "Vistta Rooftop Restaurante" not in nomes          # type fora
    assert "Duets Office Towers" not in nomes                 # type fora
    assert "Gaviões 24h" not in nomes                         # bairro fora (Aldeota)


def test_query_usa_tipo_negocio(monkeypatch):
    capturado = {}
    monkeypatch.setattr(ct, "_places_textsearch", lambda q, **k: capturado.update(q=q) or [])
    import tools.concorrentes_parque_tools as cp
    monkeypatch.setattr(cp, "listar_concorrentes_parque", lambda c, u, b: {"status": "ok", "concorrentes": []})
    ct._descobrir_concorrentes_bairro("crossfit_box", "Cocó", "Fortaleza", "CE", 0, 0)
    assert capturado["q"] == "crossfit Cocó Fortaleza CE"     # enum mapeado, não cru


def test_cross_parque_anexa_cnpj(monkeypatch):
    parque = {"status": "ok", "concorrentes": [
        {"nome": "CT Greenlife", "cnpj": "111", "telefone": "8540001111"},
    ]}
    _setup(monkeypatch, parque=parque)
    out = ct._descobrir_concorrentes_bairro("academia", "Cocó", "Fortaleza", "CE", -3.74, -38.49)
    g = next(o for o in out if o["nome"] == "CT Greenlife")
    assert g["cnpj"] == "111"
    assert g["fonte_busca"] == "places_textsearch+cnpj"
    p = next(o for o in out if o["nome"] == "Parque Esportes")
    assert p.get("cnpj") is None                              # sem match no parque
    assert p["fonte_busca"] == "places_textsearch"
