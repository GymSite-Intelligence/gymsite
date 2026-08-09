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
        from tools.google_maps_key import get_google_maps_api_key

        return "configured" if get_google_maps_api_key() else "missing"
    except Exception:
        return "error"


def _searchapi_status() -> str:
    key = (os.getenv("SEARCHAPI_KEY") or "").strip()
    return "configured" if key else "missing"


def _osm_fallback_status() -> str:
    try:
        from tools.maps_fallback import fallback_habilitado

        return "configured" if fallback_habilitado() else "off"
    except Exception:
        return "error"


def _redis_status() -> str:
    """Ping síncrono curto — ADR-006: Redis deixa de ser cego no /health.

    Não entra no conjunto critical de serving (fila degrada pra BackgroundTasks).
    """
    url = (os.getenv("REDIS_URL") or "").strip()
    if not url:
        return "missing"
    try:
        import redis as redis_sync

        client = redis_sync.from_url(
            url,
            socket_connect_timeout=1.5,
            socket_timeout=1.5,
        )
        try:
            if client.ping():
                return "ok"
            return "error"
        finally:
            try:
                client.close()
            except Exception:
                pass
    except Exception:
        return "error"


def gather_health_components(*, probe_supabase: bool = True) -> dict[str, str]:
    """Status por componente para /health e CI."""
    out: dict[str, str] = {
        "langcache": _langcache_status(),
        "gemini": _gemini_status(),
        "searchapi": _searchapi_status(),
        "osm": _osm_fallback_status(),
        "google_maps": _google_maps_status(),
        "redis": _redis_status(),
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
    # CRÍTICO = o que o trabalho da API exige. A API serve dashboard/relatório/PDF
    # (Supabase); o pipeline (gemini/maps/langcache) roda em OUTRO nó (local/worker).
    # Antes gateava em `gemini` → prod (serving, sem chave de pipeline que NÃO usa)
    # virava "degraded" à toa. supabase é o dep real de serving; os de pipeline ficam
    # visíveis nos components mas não forçam degraded num nó de serving.
    critical = {"supabase"}
    _ok_vals = ("ok", "configured", "connected", "authenticated")
    degraded = any(components.get(k) not in _ok_vals for k in critical)
    return {
        "status": "degraded" if degraded else "ok",
        "service": "gymsite-intelligence-api",
        "components": components,
    }
