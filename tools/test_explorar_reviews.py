from tools.explorar_reviews import fetch_explorar_reviews, parse_searchapi_reviews_payload

_ERROR = {
    "search_metadata": {"status": "Success"},
    "search_parameters": {
        "engine": "google_maps_reviews",
        "place_id": "ChIJCb3yfcJHxwcR0CZUhe1hc9E",
        "sort_by": "lowest_rating",
        "hl": "pt-br",
        "gl": "br",
        "num": 10,
    },
    "error": "Google Maps Reviews didn't return any results.",
}

_OK = {
    "search_parameters": {"engine": "google_maps_reviews", "place_id": "ChIJabc"},
    "reviews": [
        {"text": "Atendimento ruim", "rating": 2, "user": {"name": "Ana"}},
        {"text": "Ótima", "rating": 5, "user": {"name": "Bia"}},
    ],
}


def test_error_searchapi_nao_inventa_review():
    assert parse_searchapi_reviews_payload(_ERROR) == []
    assert parse_searchapi_reviews_payload(None) == []
    assert parse_searchapi_reviews_payload({"reviews": "oops"}) == []


def test_reviews_ok_so_lista_reviews():
    revs = parse_searchapi_reviews_payload(_OK)
    assert len(revs) == 2
    assert revs[0]["rating"] == 2


def test_fetch_explorar_reviews_respeita_error(monkeypatch):
    monkeypatch.setenv("SEARCHAPI_KEY", "k")
    seen = {}

    def fake_get(url, params=None, headers=None):
        seen["params"] = params
        class R:
            def json(self):
                return _ERROR
        return R()

    class _C:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def get(self, url, params=None, headers=None):
            return fake_get(url, params, headers)

    import tools.explorar_reviews as er
    monkeypatch.setattr(er.httpx, "Client", lambda **k: _C())
    out = fetch_explorar_reviews(place_id="ChIJCb3yfcJHxwcR0CZUhe1hc9E", data_id="0x7c:0xd1")
    assert out == []
    assert seen["params"]["engine"] == "google_maps_reviews"
    assert seen["params"]["num"] == 10
    assert seen["params"]["data_id"] == "0x7c:0xd1"
    assert seen["params"]["sort_by"] == "lowest_rating"
