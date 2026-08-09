"""
google_maps_key.py — única fonte da chave Google Maps Platform (server-side).

Use GOOGLE_MAPS_API_KEY no .env (raiz do repo ou frontend/.env; api.py carrega ambos).
Não use MAPS_API_KEY nem VITE_GOOGLE_MAPS_API_KEY — evita chaves divergentes.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def get_google_maps_api_key() -> str:
    """Retorna GOOGLE_MAPS_API_KEY trimada ou string vazia."""
    return (os.environ.get("GOOGLE_MAPS_API_KEY") or "").strip()


def warn_if_missing_maps_key() -> None:
    if get_google_maps_api_key():
        return
    logger.warning(
        "GOOGLE_MAPS_API_KEY ausente — Places/Geocoding Google off. "
        "Explorar usa Nominatim/OSM; concorrentes = SearchAPI."
    )
