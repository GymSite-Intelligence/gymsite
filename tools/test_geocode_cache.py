"""geocode_endereco cache-first: hit pula Google; miss chama Google e cacheia (#3 custo)."""
import tools.maps_tools as mt
from tools.cache_store import CacheHit


def test_cache_hit_pula_google(monkeypatch):
    chamou_google = {"v": False}

    def _fake_google(end):
        chamou_google["v"] = True
        return {"lat": 0, "lng": 0, "fonte_geocode": "google"}

    def _fake_get(chave):
        return CacheHit(hit=True, payload={"payload": {
            "lat": -3.74, "lng": -38.48, "fonte_geocode": "google", "formatted_address": "Cocó"}})

    monkeypatch.setattr(mt, "_geocode_google", _fake_google)
    monkeypatch.setattr("tools.cache_store.get_geocode", _fake_get, raising=False)

    out = mt.geocode_endereco("Cocó, Fortaleza, CE, Brasil")
    assert out["lat"] == -3.74
    assert chamou_google["v"] is False  # NÃO bateu Google
    assert out["fonte_geocode"].endswith("_cache")


def test_cache_miss_chama_google_e_cacheia(monkeypatch):
    chamou_google = {"v": False}
    setou = {"chave": None}

    def _fake_google(end):
        chamou_google["v"] = True
        return {"lat": -3.74, "lng": -38.48, "fonte_geocode": "google"}

    monkeypatch.setattr(mt, "_geocode_google", _fake_google)
    monkeypatch.setattr("tools.cache_store.get_geocode",
                        lambda c: CacheHit(hit=False, payload=None), raising=False)
    monkeypatch.setattr("tools.cache_store.set_geocode",
                        lambda *a, **k: setou.__setitem__("chave", a[0]), raising=False)

    out = mt.geocode_endereco("Aldeota, Fortaleza, CE, Brasil")
    assert out["lat"] == -3.74
    assert chamou_google["v"] is True       # bateu Google (miss)
    assert setou["chave"] == "aldeota, fortaleza, ce, brasil"  # cacheou normalizado


def test_norm_endereco():
    assert mt._norm_endereco_cache("  Cocó,  Fortaleza - CE ") == "coco, fortaleza - ce"
