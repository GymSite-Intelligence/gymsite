# tools/maps_tools.py
import os
import math
import httpx
from typing import Optional

MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY") or os.environ.get("MAPS_API_KEY", "")
PLACES_BASE = "https://places.googleapis.com/v1/places"
GEOCODING_BASE = "https://maps.googleapis.com/maps/api/geocode/json"
STREET_VIEW_BASE = "https://maps.googleapis.com/maps/api/streetview"


def geocode_endereco(endereco: str) -> dict:
    """Converte endereço em coordenadas lat/lng."""
    params = {"address": endereco, "key": MAPS_API_KEY, "language": "pt-BR", "region": "BR"}
    with httpx.Client(timeout=10) as c:
        data = c.get(GEOCODING_BASE, params=params).json()
    if data.get("status") == "OK" and data.get("results"):
        r = data["results"][0]
        loc = r["geometry"]["location"]
        return {"lat": loc["lat"], "lng": loc["lng"],
                "formatted_address": r["formatted_address"],
                "place_id": r.get("place_id", "")}
    return {"error": f"Geocoding falhou: {data.get('status')}"}


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
        "X-Goog-Api-Key": MAPS_API_KEY,
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
        "includedTypes": ["shopping_mall", "store", "supermarket", "establishment"],
        "maxResultCount": 20,
        "languageCode": "pt-BR",
    }
    with httpx.Client(timeout=15) as c:
        data = c.post(f"{PLACES_BASE}:searchNearby", json=body, headers=headers).json()

    return [_extrair_lugar(p) for p in data.get("places", [])]


def buscar_imoveis_texto(query: str, latitude: float, longitude: float,
                          raio_metros: int = 5000) -> list[dict]:
    """Text Search para imóveis comerciais: 'galpão para alugar', etc."""
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": MAPS_API_KEY,
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
    with httpx.Client(timeout=15) as c:
        data = c.post(f"{PLACES_BASE}:searchText", json=body, headers=headers).json()

    return [_extrair_lugar(p) for p in data.get("places", [])]


def obter_street_view_url(latitude: float, longitude: float,
                           width: int = 640, height: int = 400) -> str:
    """URL de imagem Street View estática."""
    return (f"{STREET_VIEW_BASE}?size={width}x{height}"
            f"&location={latitude},{longitude}&fov=90&key={MAPS_API_KEY}")


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
    if not MAPS_API_KEY or not place_id:
        return {}
    headers = {
        "X-Goog-Api-Key": MAPS_API_KEY,
        "X-Goog-FieldMask": (
            "id,nationalPhoneNumber,internationalPhoneNumber,"
            "websiteUri,regularOpeningHours,currentOpeningHours,"
            "businessStatus,priceLevel"
        ),
    }
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
