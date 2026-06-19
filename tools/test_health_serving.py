"""/health: status reflete o trabalho de SERVING (supabase), não deps de pipeline
(gemini/maps que rodam em outro nó). Prod serving sem chave de pipeline = ok, não degraded."""
import tools.health_components as hc


def test_prod_serving_ok(monkeypatch):
    """Supabase up + gemini/maps missing (prod serving) → ok (não degraded)."""
    monkeypatch.setattr(hc, "gather_health_components", lambda **k: {
        "langcache": "missing", "gemini": "missing",
        "google_maps": "missing", "supabase": "connected"})
    assert hc.health_payload()["status"] == "ok"


def test_supabase_down_degraded(monkeypatch):
    """Supabase é o dep crítico de serving — se cai, degraded."""
    monkeypatch.setattr(hc, "gather_health_components", lambda **k: {
        "supabase": "missing", "gemini": "authenticated"})
    assert hc.health_payload()["status"] == "degraded"


def test_supabase_configured_tambem_ok(monkeypatch):
    monkeypatch.setattr(hc, "gather_health_components", lambda **k: {"supabase": "configured"})
    assert hc.health_payload()["status"] == "ok"
