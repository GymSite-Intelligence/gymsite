"""Reviews: fetch raw compartilhado (memo + cache) mata o 2× (duas funções batiam o
MESMO place_id) e deixa determinístico. Causa de divergência do audit Cocó."""
import os
import httpx
import tools.competitor_tools as ct
import tools.cache_store as cs


class _Resp:
    def json(self):
        return {"reviews": [{"text": "péssimo atendimento", "rating": 1,
                             "user": {"name": "X"}, "date": "1 mês"}]}


class _Client:
    def __init__(self, *a, **k):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False
    def get(self, *a, **k):
        _Client.calls += 1
        return _Resp()


def _setup(monkeypatch):
    monkeypatch.setenv("SEARCHAPI_KEY", "fake")
    ct._REVIEWS_RAW_MEMO.clear()
    monkeypatch.setattr(cs, "get_reviews", lambda pid: cs.CacheHit(hit=False, payload=None))
    monkeypatch.setattr(cs, "set_reviews", lambda *a, **k: None)
    _Client.calls = 0
    monkeypatch.setattr(httpx, "Client", _Client)


def test_dois_consumidores_uma_chamada(monkeypatch):
    """card + baixa_nota no MESMO place_id → 1 chamada SearchAPI (memo dedup)."""
    _setup(monkeypatch)
    ct._reviews_searchapi_card("ChIJ_x", max_reviews=5)
    ct._reviews_baixa_nota_searchapi("ChIJ_x")
    assert _Client.calls == 1  # antes: 2


def test_cache_hit_zero_chamada(monkeypatch):
    """DB cache hit → zero SearchAPI (cross-run determinístico)."""
    monkeypatch.setenv("SEARCHAPI_KEY", "fake")
    ct._REVIEWS_RAW_MEMO.clear()
    monkeypatch.setattr(cs, "get_reviews",
        lambda pid: cs.CacheHit(hit=True, payload={"reviews": [{"text": "ok", "rating": 2}]}))
    _Client.calls = 0
    monkeypatch.setattr(httpx, "Client", _Client)
    out = ct._reviews_baixa_nota_searchapi("ChIJ_cached")
    assert _Client.calls == 0
    assert len(out) == 1


def test_sem_key_cai_pro_places(monkeypatch):
    """Sem SEARCHAPI_KEY → card retorna None (caller cai pro Places)."""
    monkeypatch.delenv("SEARCHAPI_KEY", raising=False)
    ct._REVIEWS_RAW_MEMO.clear()
    monkeypatch.setattr(cs, "get_reviews", lambda pid: cs.CacheHit(hit=False, payload=None))
    assert ct._reviews_searchapi_card("ChIJ_nokey") is None
