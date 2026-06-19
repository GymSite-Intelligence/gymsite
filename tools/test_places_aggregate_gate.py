"""areaInsights (Places Aggregate): preço rastreado + tracking wrap (redução de custo #1)."""
from tools.pricing import compute_places_cost_brl, PLACES_API_USD_PER_CALL


def test_sku_places_aggregate_tem_preco():
    assert "places_aggregate" in PLACES_API_USD_PER_CALL
    assert compute_places_cost_brl("places_aggregate", 1) > 0


def test_compute_insight_count_circle_rastreia(monkeypatch):
    """A chamada areaInsights agora passa por track_api_call (antes: zero track)."""
    chamado = {"sku": None}

    import contextlib

    @contextlib.contextmanager
    def _fake_track(tool, sku, n=1, **k):
        chamado["sku"] = sku
        yield

    class _Resp:
        status_code = 200
        content = b'{"count": 7}'
        def json(self):
            return {"count": 7}

    class _Client:
        def __init__(self, *a, **k):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def post(self, *a, **k):
            return _Resp()

    monkeypatch.setattr("tools.api_cost_tracker.track_api_call", _fake_track, raising=False)
    monkeypatch.setattr("tools.google_maps_key.get_google_maps_api_key", lambda: "fake-key", raising=False)
    monkeypatch.setattr("httpx.Client", _Client)

    from tools.places_aggregate_tools import compute_insight_count_circle

    out = compute_insight_count_circle(
        latitude=-3.74, longitude=-38.48, radius_meters=3000,
        included_types=["gym", "fitness_center"],
    )
    assert out.get("count") == 7
    assert chamado["sku"] == "places_aggregate"  # foi rastreado
