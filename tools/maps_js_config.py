"""Config Maps JavaScript API — chave só server-side (mesma GOOGLE_MAPS_API_KEY)."""
from __future__ import annotations

import os

from tools.google_maps_key import get_google_maps_api_key


def maps_js_config() -> dict:
    """
    Payload para o frontend carregar Maps JS + deck.gl heatmap.
    map_id opcional (Map ID no Cloud Console) para Advanced Markers.
    """
    key = get_google_maps_api_key()
    if not key:
        return {"configured": False, "key": "", "map_id": ""}
    map_id = (os.environ.get("GOOGLE_MAPS_MAP_ID") or "").strip()
    return {"configured": True, "key": key, "map_id": map_id}
