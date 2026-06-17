"""Âncora de concorrentes via SearchAPI google_maps: adapta o resultado p/ o MESMO
shape do Places searchText (places[]); injeta 'gym' no types p/ passar no filtro;
dispatcher cai pro Places se vazio."""
from unittest.mock import MagicMock, patch

import tools.competitor_tools as ct


_FAKE = {
    "local_results": [
        {"place_id": "ChIJabc", "title": "CT Greenlife", "address": "R. X - Cocó, Fortaleza - CE",
         "gps_coordinates": {"latitude": -3.74, "longitude": -38.48}, "rating": 4.0, "reviews": 63,
         "type": "Academia", "phone": "(85) 2028-4240", "website": "https://x.com", "hours": "Aberto 24 horas"},
        {"place_id": "ChIJzzz", "title": "Restaurante Tal", "address": "Av Y - Cocó, Fortaleza - CE",
         "gps_coordinates": {"latitude": -3.75, "longitude": -38.49}, "rating": 4.5, "reviews": 10,
         "type": "Restaurante"},
    ]
}


def _mock_httpx(payload):
    resp = MagicMock(); resp.json.return_value = payload
    client = MagicMock(); client.get.return_value = resp
    cm = MagicMock(); cm.__enter__.return_value = client; cm.__exit__.return_value = False
    return cm


def test_adapta_shape_places(monkeypatch):
    monkeypatch.setenv("SEARCHAPI_KEY", "k")
    with patch.object(ct.httpx, "Client", return_value=_mock_httpx(_FAKE)):
        out = ct._searchapi_maps_textsearch("academias Cocó")
    assert len(out) == 2
    p = out[0]
    # shape Places API
    assert p["id"] == "ChIJabc"
    assert p["displayName"]["text"] == "CT Greenlife"
    assert p["location"]["latitude"] == -3.74
    assert p["userRatingCount"] == 63
    assert p["nationalPhoneNumber"] == "(85) 2028-4240"
    # fitness → 'gym' injetado (passa _FITNESS_TYPES)
    assert "gym" in p["types"]
    # 24h detectável via weekdayDescriptions
    assert any("24" in h for h in p["regularOpeningHours"]["weekdayDescriptions"])


def test_restaurante_nao_recebe_gym():
    with patch.object(ct.httpx, "Client", return_value=_mock_httpx(_FAKE)):
        import os
        os.environ["SEARCHAPI_KEY"] = "k"
        out = ct._searchapi_maps_textsearch("academias Cocó")
    rest = out[1]
    assert "gym" not in rest["types"]  # restaurante filtrado pelo _FITNESS_TYPES depois


def test_dispatcher_fallback_places(monkeypatch):
    monkeypatch.setenv("COMPETIDOR_MAPS_BACKEND", "searchapi")
    with patch.object(ct, "_searchapi_maps_textsearch", return_value=[]) as sa, \
         patch.object(ct, "_places_textsearch_google", return_value=[{"id": "fallback"}]) as gg:
        out = ct._places_textsearch("q")
    sa.assert_called_once()
    gg.assert_called_once()
    assert out == [{"id": "fallback"}]


def test_dispatcher_forca_places(monkeypatch):
    monkeypatch.setenv("COMPETIDOR_MAPS_BACKEND", "places")
    with patch.object(ct, "_searchapi_maps_textsearch") as sa, \
         patch.object(ct, "_places_textsearch_google", return_value=[{"id": "g"}]) as gg:
        ct._places_textsearch("q")
    sa.assert_not_called()
    gg.assert_called_once()
