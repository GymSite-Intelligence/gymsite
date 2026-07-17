"""1 call google_maps_place → cache compartilhado pico + reviews."""
from __future__ import annotations

import json

from tools.searchapi_maps_place import (
    reviews_raw_from_maps_place,
    seed_reviews_cache_from_place,
    slim_maps_place_payload,
    set_maps_place_cache,
)
from tools.popular_times_tool import _converter_searchapi


_FAKE_PLACE = {
    "search_metadata": {"id": "search_x", "html_url": "https://huge.example/" + ("x" * 5000)},
    "search_parameters": {"engine": "google_maps_place", "place_id": "ChIJabc", "hl": "pt", "gl": "br"},
    "place_result": {
        "place_id": "ChIJabc",
        "title": "Selfit",
        "website": "https://selfit.example",
        "images": [{"title": "Tudo", "thumbnail": "https://img/" + ("y" * 2000)}],
        "posts": [{"media": "https://m/" + ("z" * 2000), "snippet": "promo"}],
        "people_also_search_for": [{"title": "Outra", "thumbnail": "https://t/1"}],
        "popular_times": {
            "chart": {
                "monday": [
                    {"time": "18:00", "busyness_score": 90},
                    {"time": "10:00", "busyness_score": 40},
                ],
            }
        },
        "review_results": {
            "summaries": ["limpa", "lotada"],
            "reviews": [
                {
                    "rating": 5,
                    "description": "Ótima academia limpa",
                    "user": {
                        "name": "Ana",
                        "thumbnail": "https://u/" + ("a" * 500),
                        "link": "https://maps/contrib/1",
                    },
                    "date": "1 mês atrás",
                    "images": ["https://r/1"],
                },
                {
                    "rating": 1,
                    "description": "Lotada e suja demais",
                    "user": {"name": "Bob"},
                    "date": "2 meses atrás",
                },
            ]
        },
    },
}


def test_reviews_from_place_ordena_baixa_nota():
    revs = reviews_raw_from_maps_place(_FAKE_PLACE)
    assert len(revs) == 2
    assert revs[0]["rating"] == 1
    assert "Lotada" in revs[0]["text"]
    assert revs[0]["user"]["name"] == "Bob"


def test_converter_pico_do_mesmo_payload():
    out = _converter_searchapi(_FAKE_PLACE, "ChIJabc")
    assert out["status"] == "ok"
    assert out["fonte"] == "searchapi"
    assert out["dados_por_dia"]["segunda"]["18"] == 90


def test_fetch_reviews_bundle_usa_place_sem_reviews_engine(monkeypatch):
    import tools.competitor_tools as ct

    ct._REVIEWS_BUNDLE_MEMO.clear()
    monkeypatch.setattr(
        "tools.searchapi_maps_place.get_or_fetch_maps_place",
        lambda pid, **k: _FAKE_PLACE,
    )
    monkeypatch.setattr(
        "tools.cache_store.get_reviews",
        lambda pid: type("H", (), {"hit": False, "payload": None})(),
    )
    monkeypatch.setattr("tools.cache_store.set_reviews", lambda *a, **k: None)
    called = {"reviews_engine": False}

    class _Boom:
        def __init__(self, *a, **k):
            called["reviews_engine"] = True
            raise AssertionError("não deve chamar google_maps_reviews")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(ct.httpx, "Client", _Boom)
    bundle = ct._fetch_reviews_bundle("ChIJabc")
    assert bundle is not None
    assert len(bundle["reviews"]) == 2
    assert bundle["reviews"][0]["rating"] == 1
    assert called["reviews_engine"] is False


def test_seed_reviews_cache(monkeypatch):
    saved = {}

    def fake_set(pid, reviews, *, topics=None, source="searchapi", ttl_days=7):
        saved["pid"] = pid
        saved["n"] = len(reviews)
        saved["source"] = source

    monkeypatch.setattr("tools.cache_store.set_reviews", fake_set)
    seed_reviews_cache_from_place("ChIJabc", _FAKE_PLACE)
    assert saved["pid"] == "ChIJabc"
    assert saved["n"] == 2
    assert saved["source"] == "searchapi_google_maps_place"


def test_slim_drops_media_keeps_pico_reviews():
    slim = slim_maps_place_payload(_FAKE_PLACE)
    pr = slim["place_result"]
    assert "images" not in pr
    assert "posts" not in pr
    assert "people_also_search_for" not in pr
    assert "search_metadata" not in slim
    assert pr["website"] == "https://selfit.example"
    assert "popular_times" in pr
    rev0 = pr["review_results"]["reviews"][0]
    assert rev0["user"] == {"name": "Ana"}
    assert "thumbnail" not in rev0["user"]
    assert "images" not in rev0
    raw_n = len(json.dumps(_FAKE_PLACE, ensure_ascii=False))
    slim_n = len(json.dumps(slim, ensure_ascii=False))
    assert slim_n < raw_n // 2
    assert reviews_raw_from_maps_place(slim)[0]["rating"] == 1
    assert _converter_searchapi(slim, "ChIJabc")["dados_por_dia"]["segunda"]["18"] == 90


def test_set_maps_place_cache_writes_slim_and_logs_fail(monkeypatch, caplog):
    written = {}

    def fake_set(pid, payload, **kw):
        written["pid"] = pid
        written["payload"] = payload
        written["source"] = kw.get("source")

    monkeypatch.setattr("tools.cache_store.set_places_details", fake_set)
    assert set_maps_place_cache("ChIJabc", _FAKE_PLACE) is True
    assert written["pid"] == "ChIJabc"
    assert "images" not in written["payload"]["place_result"]
    assert written["source"] == "searchapi_google_maps_place"

    def boom(*a, **k):
        raise RuntimeError("payload too large")

    monkeypatch.setattr("tools.cache_store.set_places_details", boom)
    with caplog.at_level("WARNING"):
        assert set_maps_place_cache("ChIJabc", _FAKE_PLACE) is False
    assert any("upsert fail" in r.message for r in caplog.records)
