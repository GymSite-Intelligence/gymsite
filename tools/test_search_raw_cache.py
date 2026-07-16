"""Testes search_raw_cache — hash estável e round-trip best-effort."""

from tools.search_raw_cache import params_hash


def test_params_hash_stable():
    h1 = params_hash("google_maps", {"q": "academias Cocó Fortaleza CE", "gl": "br", "hl": "pt-br"})
    h2 = params_hash("google_maps", {"hl": "pt-br", "q": "academias Cocó Fortaleza CE", "gl": "br"})
    assert h1 == h2
    assert len(h1) == 64


def test_params_hash_engine_sensitive():
    a = params_hash("google_maps", {"q": "x"})
    b = params_hash("google_maps_reviews", {"q": "x"})
    assert a != b
