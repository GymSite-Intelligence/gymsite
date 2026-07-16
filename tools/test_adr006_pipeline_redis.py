"""ADR-006: redis no /health + publish_pipeline_progress_sync (mock)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import tools.health_components as hc


def test_gather_includes_redis(monkeypatch):
    monkeypatch.setattr(hc, "_langcache_status", lambda: "missing")
    monkeypatch.setattr(hc, "_gemini_status", lambda: "missing")
    monkeypatch.setattr(hc, "_google_maps_status", lambda: "missing")
    monkeypatch.setattr(hc, "_supabase_status", lambda: "connected")
    monkeypatch.setattr(hc, "_redis_status", lambda: "ok")
    comps = hc.gather_health_components(probe_supabase=True)
    assert comps["redis"] == "ok"
    assert comps["supabase"] == "connected"


def test_redis_down_does_not_degrade_serving(monkeypatch):
    """Redis visível mas não critical — serving segue ok se supabase up."""
    monkeypatch.setattr(
        hc,
        "gather_health_components",
        lambda **k: {
            "langcache": "missing",
            "gemini": "missing",
            "google_maps": "missing",
            "supabase": "connected",
            "redis": "error",
        },
    )
    assert hc.health_payload()["status"] == "ok"
    assert hc.health_payload()["components"]["redis"] == "error"


def test_redis_status_missing_without_url(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    assert hc._redis_status() == "missing"


def test_publish_pipeline_progress_sync_writes_channel_and_hash(monkeypatch):
    from tools import redis_pubsub as rp

    fake = MagicMock()
    monkeypatch.setattr(rp, "_sync_redis", lambda: fake)

    rp.publish_pipeline_progress_sync(
        relatorio_id="rid-1",
        agent_id="ContextBuilder",
        status="running",
    )

    assert fake.publish.call_count == 2
    channel, payload = fake.publish.call_args_list[0][0]
    assert channel == "gymsite:pipeline:rid-1"
    event = json.loads(payload)
    assert event["v"] == 1
    assert event["type"] == "agent.progress"
    assert event["agent_id"] == "ContextBuilder"
    assert event["status"] == "running"

    fake.hset.assert_called_once()
    key, field, blob = fake.hset.call_args[0]
    assert key == "gymsite:pipeline:state:rid-1"
    assert field == "ContextBuilder"
    assert json.loads(blob)["status"] == "running"
    fake.expire.assert_called_once_with(key, rp.PIPELINE_STATE_TTL_SEC)
    fake.close.assert_called_once()


def test_publish_pipeline_progress_sync_swallows_redis_errors(monkeypatch):
    from tools import redis_pubsub as rp

    def boom():
        raise ConnectionError("down")

    monkeypatch.setattr(rp, "_sync_redis", boom)
    # não levanta
    rp.publish_pipeline_progress_sync(
        relatorio_id="rid-2",
        agent_id="GeoScout",
        status="completed",
        latency_ms=1200,
    )
