"""Geo fields: slim payload, writer rows, re-gravação preserva coords."""
from db.supabase_writer import (
    _merge_competidor_geo_row,
    _norm_coord,
    _rows_competidores,
)
from tools.competitor_tools import _slim_concorrente


def _relatorio_min(competitors_set: list[dict]) -> dict:
    return {
        "output_consolidado": {
            "competitors_set": competitors_set,
        },
    }


def test_rows_competidores_normaliza_coords():
    rel = _relatorio_min(
        [
            {
                "nome": "Gym A",
                "place_id": "ChIJ_a",
                "lat": -3.73,
                "lng": -38.52,
                "distancia_km": 1.256,
                "google_maps_uri": "https://maps.example/a",
                "reviews": [],
            }
        ]
    )
    rows = _rows_competidores(rel, "00000000-0000-0000-0000-000000000099")
    assert len(rows) == 1
    r = rows[0]
    assert r["place_id"] == "ChIJ_a"
    assert r["lat"] == -3.73
    assert r["lng"] == -38.52
    assert r["distancia_km"] == 1.26
    assert r["google_maps_uri"] == "https://maps.example/a"


def test_rows_competidores_descarta_zero_zero():
    rel = _relatorio_min([{"nome": "Gym B", "lat": 0, "lng": 0, "reviews": []}])
    rows = _rows_competidores(rel, "00000000-0000-0000-0000-000000000099")
    assert rows[0]["lat"] is None
    assert rows[0]["lng"] is None


def test_geo_preserve_mantem_lat_lng_quando_payload_sem_coords():
    row = {
        "relatorio_id": "rid",
        "nome": "Smart Fit X",
        "place_id": "ChIJ_keep",
        "lat": None,
        "lng": None,
    }
    lookup = {
        "chij_keep": {
            "place_id": "ChIJ_keep",
            "lat": -3.5,
            "lng": -38.4,
            "distancia_km": 2.0,
            "google_maps_uri": "https://maps.example/keep",
        }
    }
    merged = _merge_competidor_geo_row(row, lookup)
    assert merged["lat"] == -3.5
    assert merged["lng"] == -38.4
    assert merged["distancia_km"] == 2.0
    assert merged["google_maps_uri"] == "https://maps.example/keep"


def test_geo_preserve_nao_sobrescreve_coords_novas():
    row = {
        "nome": "Gym",
        "place_id": "ChIJ_new",
        "lat": -3.1,
        "lng": -38.1,
    }
    lookup = {
        "chij_new": {"lat": -9.0, "lng": -40.0, "place_id": "ChIJ_old"},
    }
    merged = _merge_competidor_geo_row(row, lookup)
    assert merged["lat"] == -3.1
    assert merged["lng"] == -38.1
    assert merged["place_id"] == "ChIJ_new"


def test_slim_e_writer_alinhados():
    raw = {
        "nome": "Academia Z",
        "place_id": "ChIJ_z",
        "lat": -3.8,
        "lng": -38.6,
        "distancia_km": 0.5,
        "google_maps_uri": "https://maps.example/z",
        "reviews": [],
    }
    slim = _slim_concorrente(raw)
    rows = _rows_competidores(_relatorio_min([slim]), "rid")
    assert rows[0]["lat"] == slim["lat"]
    assert rows[0]["lng"] == slim["lng"]
    assert rows[0]["place_id"] == slim["place_id"]


def test_norm_coord():
    assert _norm_coord(0) is None
    assert _norm_coord(-3.5) == -3.5
    assert _norm_coord("bad") is None
