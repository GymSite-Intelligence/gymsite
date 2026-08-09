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


def test_searchapi_e_osm_no_health_sem_probe_google(monkeypatch):
    monkeypatch.setenv("SEARCHAPI_KEY", "sk_test")
    monkeypatch.setenv("MAPS_FALLBACK_ENABLED", "1")
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    monkeypatch.setattr(hc, "_langcache_status", lambda: "missing")
    monkeypatch.setattr(hc, "_gemini_status", lambda: "missing")
    monkeypatch.setattr(hc, "_redis_status", lambda: "ok")
    monkeypatch.setattr(hc, "_supabase_status", lambda: "connected")
    comps = hc.gather_health_components(probe_supabase=True)
    assert comps["searchapi"] == "configured"
    assert comps["osm"] == "configured"
    assert comps["google_maps"] == "missing"
