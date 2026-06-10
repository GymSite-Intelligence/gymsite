"""Campos geo preservados em _slim_concorrente (mapa municipal)."""
from tools.competitor_tools import _slim_concorrente


def test_slim_preserva_coords_e_place_id():
    raw = {
        "nome": "Academia X",
        "place_id": "ChIJabc",
        "lat": -3.73,
        "lng": -38.52,
        "distancia_km": 1.25,
        "google_maps_uri": "https://maps.google.com/?cid=1",
        "endereco": "Rua A, 1",
        "rating_oficial": 4.5,
        "num_avaliacoes": 120,
        "reviews": [],
    }
    slim = _slim_concorrente(raw)
    assert slim["place_id"] == "ChIJabc"
    assert slim["lat"] == -3.73
    assert slim["lng"] == -38.52
    assert slim["distancia_km"] == 1.25
    assert slim["google_maps_uri"] == "https://maps.google.com/?cid=1"


def test_slim_descarta_zero_zero():
    slim = _slim_concorrente({"nome": "Y", "lat": 0.0, "lng": 0.0, "reviews": []})
    assert slim.get("lat") is None
    assert slim.get("lng") is None
