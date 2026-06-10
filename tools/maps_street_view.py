"""
Street View Static — URLs públicas via proxy da API (chave só no servidor).
"""
from __future__ import annotations

import os

from tools.google_maps_key import get_google_maps_api_key

STREET_VIEW_BASE = "https://maps.googleapis.com/maps/api/streetview"


def street_view_proxy_enabled() -> bool:
    """Padrão: proxy ativo quando há chave Google (evita expor key no JSON)."""
    raw = os.getenv("MAPS_STREET_VIEW_PROXY", "").strip().lower()
    if raw in ("0", "false", "no"):
        return False
    if raw in ("1", "true", "yes"):
        return True
    return bool(get_google_maps_api_key())


def build_street_view_proxy_url(
    latitude: float,
    longitude: float,
    *,
    width: int = 640,
    height: int = 400,
    api_base: str | None = None,
) -> str:
    """URL relativa ou absoluta para o endpoint proxy da API."""
    base = (api_base or os.getenv("GYMSITE_API_PUBLIC_URL", "").strip()).rstrip("/")
    path = (
        f"/api/maps/street-view?lat={latitude}&lng={longitude}"
        f"&w={int(width)}&h={int(height)}"
    )
    return f"{base}{path}" if base else path


def build_street_view_google_url(
    latitude: float,
    longitude: float,
    *,
    width: int = 640,
    height: int = 400,
) -> str:
    key = get_google_maps_api_key()
    return (
        f"{STREET_VIEW_BASE}?size={width}x{height}"
        f"&location={latitude},{longitude}&fov=90&key={key}"
    )
