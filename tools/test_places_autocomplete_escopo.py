"""escopo bairro vs endereco no proxy Places."""
from __future__ import annotations


class _FakeResp:
    status_code = 200
    text = "{}"

    def json(self):
        return {"suggestions": []}


def _patch_client(monkeypatch, captured: dict):
    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, headers=None, json=None):
            captured["json"] = json
            return _FakeResp()

    monkeypatch.setattr("tools.places_autocomplete.get_google_maps_api_key", lambda: "fake")
    monkeypatch.setattr("tools.places_autocomplete.httpx.Client", FakeClient)


def test_escopo_bairro_restringe_tipos(monkeypatch):
    captured: dict = {}
    _patch_client(monkeypatch, captured)
    from tools.places_autocomplete import places_autocomplete

    places_autocomplete("Coco", municipio="Fortaleza", uf="CE")
    assert captured["json"]["includedPrimaryTypes"] == ["sublocality", "neighborhood"]


def test_escopo_endereco_nao_restringe_tipos(monkeypatch):
    captured: dict = {}
    _patch_client(monkeypatch, captured)
    from tools.places_autocomplete import places_autocomplete

    places_autocomplete("Coco", escopo="endereco", lat=-3.7455, lng=-38.4855)
    assert "includedPrimaryTypes" not in captured["json"]
    assert captured["json"]["input"] == "Coco"
    assert captured["json"]["locationBias"]["circle"]["center"]["latitude"] == -3.7455
