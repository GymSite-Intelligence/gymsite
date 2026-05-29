# tools/maps_tools.py
import logging
import math
import httpx
from typing import Optional

from tools.google_maps_key import get_google_maps_api_key

logger = logging.getLogger(__name__)

PLACES_BASE = "https://places.googleapis.com/v1/places"
GEOCODING_BASE = "https://maps.googleapis.com/maps/api/geocode/json"
STREET_VIEW_BASE = "https://maps.googleapis.com/maps/api/streetview"


def _geocode_google(endereco: str) -> dict:
    key = get_google_maps_api_key()
    if not key:
        return {"error": "GOOGLE_MAPS_API_KEY ausente"}
    params = {
        "address": endereco,
        "key": key,
        "language": "pt-BR",
        "region": "BR",
    }
    from tools.api_cost_tracker import track_api_call
    with track_api_call("geocode_google", "geocoding", 1):
        with httpx.Client(timeout=10) as c:
            data = c.get(GEOCODING_BASE, params=params).json()
    if data.get("status") == "OK" and data.get("results"):
        r = data["results"][0]
        loc = r["geometry"]["location"]
        return {
            "lat": loc["lat"],
            "lng": loc["lng"],
            "formatted_address": r["formatted_address"],
            "place_id": r.get("place_id", ""),
            "fonte_geocode": "google",
        }
    msg = data.get("error_message") or data.get("status")
    return {"error": f"Geocoding falhou: {data.get('status')}", "detail": msg}


def geocode_endereco(endereco: str) -> dict:
    """Converte endereço em lat/lng (Google → fallback Nominatim/OSM)."""
    result = _geocode_google(endereco)
    if "error" not in result:
        return result
    try:
        from tools.maps_fallback import fallback_habilitado, geocode_nominatim

        if fallback_habilitado():
            fb = geocode_nominatim(endereco)
            if "error" not in fb:
                logger.warning(
                    "Geocode Google indisponível (%s) — usando Nominatim para: %s",
                    result.get("error"),
                    endereco[:60],
                )
                return fb
    except Exception as exc:
        logger.debug("fallback geocode falhou: %s", exc)
    return result


def _extrair_lugar(p: dict) -> dict:
    """
    Normaliza um Place do Places API New v1 em dict consumível pelo pipeline.
    Inclui Contact Data (telefone, website, horários) — fix do bug onde A5
    recebia "N/A" mesmo quando o Google tinha o dado (caso CiaCar — Itajaí).
    """
    horarios = p.get("regularOpeningHours") or {}
    periodos = horarios.get("weekdayDescriptions") or []
    tem_24h = any("24" in h for h in periodos) if periodos else False
    return {
        "place_id": p.get("id", ""),
        "nome": p.get("displayName", {}).get("text", ""),
        "endereco": p.get("formattedAddress", ""),
        "lat": p.get("location", {}).get("latitude", 0),
        "lng": p.get("location", {}).get("longitude", 0),
        "tipos": p.get("types", []),
        "status": p.get("businessStatus", ""),
        "rating": p.get("rating"),
        "num_avaliacoes": p.get("userRatingCount", 0),
        # Contact Data — antes ausente no FieldMask; agora propagado pra A5.
        # +$3/1k requests no pricing Places API (Contact Data SKU). Vale a pena
        # pra o decisor não receber "N/A" quando o Google tem o telefone.
        "telefone": p.get("nationalPhoneNumber", ""),
        "website": p.get("websiteUri", ""),
        "tem_24h": tem_24h,
        "horarios": periodos[:3],
    }


def buscar_pontos_comerciais(latitude: float, longitude: float,
                              raio_metros: int = 5000) -> list[dict]:
    """Nearby Search por espaços comerciais candidatos."""
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": get_google_maps_api_key(),
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,"
            "places.location,places.types,places.businessStatus,"
            "places.rating,places.userRatingCount,"
            # Contact Data — adicionado pra A5 ContactHunter ter telefone
            # real do candidato em vez de "N/A". Sobe SKU pricing Places.
            "places.nationalPhoneNumber,places.websiteUri,places.regularOpeningHours"
        ),
    }
    body = {
        "locationRestriction": {"circle": {
            "center": {"latitude": latitude, "longitude": longitude},
            "radius": float(raio_metros),
        }},
        "includedTypes": ["shopping_mall", "store", "supermarket"],  # removed 'establishment' due to API 400 error
        "maxResultCount": 20,
        "languageCode": "pt-BR",
    }
    from tools.api_cost_tracker import track_api_call
    with track_api_call("buscar_pontos_comerciais", "places_search_new", 1):
        with httpx.Client(timeout=15) as c:
            resp = c.post(f"{PLACES_BASE}:searchNearby", json=body, headers=headers)
            data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}

    if resp.status_code == 200 and data.get("places"):
        return [_extrair_lugar(p) for p in data.get("places", [])]

    try:
        from tools.maps_fallback import fallback_habilitado, overpass_fitness_near

        if fallback_habilitado():
            fb = overpass_fitness_near(latitude, longitude, raio_metros, limit=20)
            if fb.get("places"):
                logger.warning("Places Nearby indisponível — fallback Overpass (%s lugares)", len(fb["places"]))
                return fb["places"]
    except Exception as exc:
        logger.debug("fallback nearby falhou: %s", exc)
    return []


def buscar_imoveis_texto(query: str, latitude: float, longitude: float,
                          raio_metros: int = 5000) -> list[dict]:
    """Text Search para imóveis comerciais: 'galpão para alugar', etc."""
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": get_google_maps_api_key(),
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,"
            "places.location,places.types,places.businessStatus,"
            "places.rating,places.userRatingCount,"
            "places.nationalPhoneNumber,places.websiteUri,places.regularOpeningHours"
        ),
    }
    body = {
        "textQuery": query,
        "locationBias": {"circle": {
            "center": {"latitude": latitude, "longitude": longitude},
            "radius": float(raio_metros),
        }},
        "maxResultCount": 10,
        "languageCode": "pt-BR",
    }
    from tools.api_cost_tracker import track_api_call
    with track_api_call("buscar_imoveis_texto", "places_search_new", 1):
        with httpx.Client(timeout=15) as c:
            resp = c.post(f"{PLACES_BASE}:searchText", json=body, headers=headers)
            data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}

    if resp.status_code == 200 and data.get("places"):
        return [_extrair_lugar(p) for p in data.get("places", [])]

    try:
        from tools.maps_fallback import fallback_habilitado, overpass_fitness_near

        if fallback_habilitado():
            fb = overpass_fitness_near(latitude, longitude, raio_metros, limit=10)
            if fb.get("places"):
                logger.warning("Places Text Search indisponível — fallback Overpass")
                return fb["places"]
    except Exception as exc:
        logger.debug("fallback text search falhou: %s", exc)
    return []


def obter_street_view_url(latitude: float, longitude: float,
                           width: int = 640, height: int = 400) -> str:
    """URL de imagem Street View estática."""
    return (f"{STREET_VIEW_BASE}?size={width}x{height}"
            f"&location={latitude},{longitude}&fov=90&key={get_google_maps_api_key()}")


def obter_detalhes_contato(place_id: str) -> dict:
    """
    GET /places/{place_id} — Places API New v1, pega Contact Data confiável.

    Por que existe (refinamento Itajaí Cordeiros — CiaCar):
    searchNearby da Places API New retorna `nationalPhoneNumber`, `websiteUri`
    e `regularOpeningHours` INCONSISTENTEMENTE mesmo com FieldMask correto.
    Pra Contact Data confiável, o caminho é Place Details individual.

    Trade-off: +1 request por candidato enriquecido. Pricing Places API New
    Contact Data = $3/1k requests. Usar apenas no Top 3 mantém custo baixo
    (~$0.01 por análise).

    Returns:
        Dict com telefone, website, tem_24h, horarios (lista de strings),
        aberto_agora, business_status. Vazio em caso de erro/quota.
    """
    if not get_google_maps_api_key() or not place_id:
        return {}
    headers = {
        "X-Goog-Api-Key": get_google_maps_api_key(),
        "X-Goog-FieldMask": (
            "id,nationalPhoneNumber,internationalPhoneNumber,"
            "websiteUri,regularOpeningHours,currentOpeningHours,"
            "businessStatus,priceLevel"
        ),
    }
    from tools.api_cost_tracker import track_api_call
    with track_api_call("obter_detalhes_contato", "places_details_new", 1):
        try:
            with httpx.Client(timeout=10) as c:
                r = c.get(f"{PLACES_BASE}/{place_id}",
                          headers=headers, params={"languageCode": "pt-BR"})
                if r.status_code != 200:
                    return {"erro": f"HTTP {r.status_code}: {r.text[:200]}"}
                data = r.json()
        except Exception as e:
            return {"erro": f"Places Details falhou: {type(e).__name__}: {e}"}

    regulares = data.get("regularOpeningHours") or {}
    periods = regulares.get("periods") or []
    weekday = regulares.get("weekdayDescriptions") or []
    # 24h: 1 período sem `close` (formato Places API New)
    tem_24h = len(periods) == 1 and "close" not in periods[0]
    current = data.get("currentOpeningHours") or {}

    return {
        "telefone": data.get("nationalPhoneNumber", ""),
        "telefone_intl": data.get("internationalPhoneNumber", ""),
        "website": data.get("websiteUri", ""),
        "tem_24h": tem_24h,
        "horarios": weekday,
        "aberto_agora": current.get("openNow"),
        "business_status": data.get("businessStatus", ""),
        "price_level": data.get("priceLevel", ""),
    }


def calcular_distancia_km(lat1: float, lng1: float,
                           lat2: float, lng2: float) -> float:
    """Distância entre dois pontos (Haversine)."""
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
