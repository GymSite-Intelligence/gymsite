"""Config Maps JavaScript API — chave de NAVEGADOR, separada da chave server.

A chave entregue aqui vai para todo visitante do mapa (é pública por natureza)
e por isso deve ser uma chave restrita por REFERRER e limitada à Maps
JavaScript API no Cloud Console. NUNCA aplicar restrição por IP nesta chave
nem reusar a chave server (Places/Geocoding/StreetView) aqui.
"""
from __future__ import annotations

import os

from tools.google_maps_key import get_google_maps_api_key


def maps_js_config() -> dict:
    """
    Payload para o frontend carregar Maps JS + deck.gl heatmap.
    map_id opcional (Map ID no Cloud Console) para Advanced Markers.
    Fallback para GOOGLE_MAPS_API_KEY mantém o mapa vivo até o split de
    chaves ser concluído no Cloud Console.
    """
    key = (os.environ.get("GOOGLE_MAPS_BROWSER_KEY") or "").strip() or get_google_maps_api_key()
    if not key:
        return {"configured": False, "key": "", "map_id": ""}
    map_id = (os.environ.get("GOOGLE_MAPS_MAP_ID") or "").strip()
    return {"configured": True, "key": key, "map_id": map_id}
