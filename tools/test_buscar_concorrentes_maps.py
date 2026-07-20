"""Formato 1: query tipada = link Maps; gates tipo+bairro determinísticos."""
from __future__ import annotations

import tools.competitor_tools as ct
from agents_site.tools import buscar_concorrentes


def _fake_place(title: str, address: str, *, place_id: str = "ChIJx", tipos=None) -> dict:
    return {
        "id": place_id,
        "displayName": {"text": title},
        "formattedAddress": address,
        "location": {"latitude": -3.74, "longitude": -38.48},
        "types": tipos or ["gym", "Academia"],
        "rating": 4.0,
        "userRatingCount": 10,
        "_fonte_textsearch": "searchapi_google_maps",
    }


def test_query_formato1_e_url_1_a_1():
    q = ct._query_formato1("academia", "Cocó", "Fortaleza", "CE")
    assert q == "academia no bairro Cocó, Fortaleza - CE"
    url = ct._maps_search_url_from_query(q)
    assert url == (
        "https://www.google.com/maps/search/"
        "academia+no+bairro+Coc%C3%B3%2C+Fortaleza+-+CE/"
    )


def test_buscar_concorrentes_formato1_query_gates_e_url(monkeypatch):
    captured: dict = {}

    def fake_ts(query: str, **kwargs):
        captured["query"] = query
        captured["kwargs"] = kwargs
        return [
            _fake_place("Academia Uniq Club Cocó", "R. X - Cocó, Fortaleza - CE", place_id="a"),
            _fake_place("Keep in shape Academia", "R. Z - Cocó, Fortaleza - CE", place_id="d"),
            _fake_place(
                "REK CrossFit Cocó",
                "R. Y - Cocó, Fortaleza - CE",
                place_id="b",
                tipos=["gym", "Crossfit"],
            ),
            _fake_place("Max Forma", "Av. Z - Aldeota, Fortaleza - CE", place_id="c"),
        ]

    monkeypatch.setattr(ct, "_places_textsearch", fake_ts)
    monkeypatch.setattr(
        ct,
        "geocode_endereco",
        lambda _e: {"lat": -3.74, "lng": -38.48, "fonte_geocode": "test"},
    )
    import tools.concorrentes_parque_tools as cp

    monkeypatch.setattr(
        cp,
        "listar_concorrentes_parque",
        lambda *a, **k: {"status": "ok", "concorrentes": []},
    )

    out = buscar_concorrentes("Fortaleza", "Cocó", "CE", "academia")
    assert captured["query"] == "academia no bairro Cocó, Fortaleza - CE"
    assert out["query"] == "academia no bairro Cocó, Fortaleza - CE"
    assert out["maps_smoke_url"] == ct._maps_search_url_from_query(out["query"])
    assert out["total_concorrentes"] == 2
    nomes = {c["nome"] for c in out["concorrentes"]}
    assert "Academia Uniq Club Cocó" in nomes
    assert "Keep in shape Academia" in nomes
    assert "REK CrossFit Cocó" not in nomes
    assert "crossfit" in out["exclude_aplicado"]
