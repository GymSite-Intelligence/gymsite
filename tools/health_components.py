"""Component health probes for /health (no heavy external calls by default)."""
from __future__ import annotations

import os
from typing import Any


def _gemini_status() -> str:
    use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    if use_vertex:
        project = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
        return "authenticated" if project else "missing"

    key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    if not key:
        return "missing"
    if key.startswith("AQ."):
        return "invalid_key"
    return "configured"


def _langcache_status() -> str:
    try:
        from tools.langcache_client import is_langcache_configured

        return "configured" if is_langcache_configured() else "missing"
    except Exception:
        return "error"


def _supabase_status() -> str:
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        return "missing"
    try:
        from db.supabase_writer import _get_client

        client = _get_client()
        if client is None:
            return "error"
        # Ping leve — falha de rede vira "error", não derruba o processo.
        client.table("relatorios").select("id").limit(1).execute()
        return "connected"
    except Exception:
        return "error"


def _google_maps_status() -> str:
    try:
        from tools.maps_health import check_google_maps

        diag = check_google_maps()
        if diag.get("ok"):
            return "ok"
        if not diag.get("configured"):
            return "missing"
        return "error"
    except Exception:
        return "error"


def gather_health_components(*, probe_supabase: bool = True) -> dict[str, str]:
    """Status por componente para /health e CI."""
    out: dict[str, str] = {
        "langcache": _langcache_status(),
        "gemini": _gemini_status(),
        "google_maps": _google_maps_status(),
    }
    if probe_supabase:
        out["supabase"] = _supabase_status()
    else:
        url = os.getenv("SUPABASE_URL", "").strip()
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        out["supabase"] = "configured" if url and key else "missing"
    return out


def health_payload(*, probe_supabase: bool = True) -> dict[str, Any]:
    components = gather_health_components(probe_supabase=probe_supabase)
    critical = {"gemini"}
    degraded = any(components.get(k) in ("missing", "invalid_key", "error") for k in critical)
    return {
        "status": "degraded" if degraded else "ok",
        "service": "gymsite-intelligence-api",
        "components": components,
    }
