"""Deep A3a: reviews via SearchAPI google_maps_place, sem Places Details."""
from __future__ import annotations

from tools.searchapi_maps_place import contato_from_maps_place
import tools.competitor_tools as ct

_FAKE_PLACE = {
    "search_parameters": {"engine": "google_maps_place", "place_id": "ChIJabc"},
    "place_result": {
        "place_id": "ChIJabc",
        "title": "Selfit",
        "website": "https://selfit.example",
        "phone": "+55 85 99999-0000",
        "review_results": {
            "reviews": [
                {"rating": 5, "description": "Ótima academia limpa", "user": {"name": "Ana"}, "date": "1 mês atrás"},
                {"rating": 1, "description": "Lotada e suja demais", "user": {"name": "Bob"}, "date": "2 meses atrás"},
            ]
        },
    },
}


def test_contato_from_maps_place():
    c = contato_from_maps_place(_FAKE_PLACE)
    assert c["website"] == "https://selfit.example"


def test_deep_usa_place_nao_chama_reviews_engine_nem_places(monkeypatch):
    ct._REVIEWS_BUNDLE_MEMO.clear()
    called = {"reviews_engine": False, "places": False}

    def _boom_fetch(*a, **k):
        called["reviews_engine"] = True
        raise AssertionError("não deve chamar google_maps_reviews")

    monkeypatch.setattr(ct, "_reviews_searchapi_card", _boom_fetch)
    monkeypatch.setattr(ct, "buscar_reviews_academia", lambda *a, **k: called.__setitem__("places", True) or {})

    out = ct.reviews_deep_searchapi("ChIJabc", _FAKE_PLACE)
    assert out["fonte_reviews"] == "searchapi_google_maps_place"
    assert len(out["reviews"]) == 2
    assert out["reviews"][0]["rating"] == 1  # dores primeiro
    assert out["website"] == "https://selfit.example"
    assert called["reviews_engine"] is False
    assert called["places"] is False


def test_deep_fallback_reviews_engine_quando_place_sem_reviews(monkeypatch):
    ct._REVIEWS_BUNDLE_MEMO.clear()
    fake_cards = [{
        "rating": 2, "quote_curta": "ruim", "sentimento": "negativo",
        "dores_detectadas": [], "servicos_mencionados": [],
        "autor": "X", "data_relativa": "",
    }]
    empty_place = {"place_result": {"place_id": "ChIJx", "title": "Gym", "website": "https://g.example"}}

    monkeypatch.setattr(ct, "_reviews_searchapi_card", lambda *a, **k: fake_cards)
    monkeypatch.setattr(
        "tools.searchapi_maps_place.get_or_fetch_maps_place",
        lambda pid, **k: empty_place,
    )

    out = ct.reviews_deep_searchapi("ChIJx", empty_place)
    assert out["fonte_reviews"] == "searchapi_google_maps_reviews"
    assert out["reviews"] == fake_cards
    assert out["website"] == "https://g.example"


def test_deep_nao_cai_em_places_details(monkeypatch):
    """Sem SearchAPI reviews → lista vazia honesta, não Places Details."""
    ct._REVIEWS_BUNDLE_MEMO.clear()
    monkeypatch.setattr(ct, "_reviews_searchapi_card", lambda *a, **k: None)
    monkeypatch.setattr(
        "tools.searchapi_maps_place.get_or_fetch_maps_place",
        lambda pid, **k: {"place_result": {"place_id": pid, "title": "X"}},
    )
    places_called = []
    monkeypatch.setattr(
        ct,
        "buscar_reviews_academia",
        lambda *a, **k: places_called.append(1) or {"reviews": [{"rating": 5}]},
    )
    out = ct.reviews_deep_searchapi("ChIJz", {"place_result": {"place_id": "ChIJz"}})
    assert out["reviews"] == []
    assert out["fonte_reviews"] == "indisponivel"
    assert places_called == []
