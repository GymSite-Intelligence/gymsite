# tools/maps_tools.py
import hashlib
import json as _json_cache
import logging
import math
import time as _time_cache
from pathlib import Path

import httpx
from typing import Optional

from tools.google_maps_key import get_google_maps_api_key

logger = logging.getLogger(__name__)

PLACES_BASE = "https://places.googleapis.com/v1/places"
GEOCODING_BASE = "https://maps.googleapis.com/maps/api/geocode/json"
STREET_VIEW_BASE = "https://maps.googleapis.com/maps/api/streetview"

# Cache disk das buscas Places (12/06): re-run do mesmo bairro pagava as
# mesmas buscas de novo (Bessa rodou 3x num dia). TTL 12h equilibra custo
# vs frescor de listing/âncora.
_PLACES_CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "places_search_cache"
_PLACES_CACHE_TTL_SEC = 12 * 3600


def _places_cache_get(chave: str) -> list | None:
    try:
        h = hashlib.sha1(chave.encode("utf-8")).hexdigest()[:24]
        p = _PLACES_CACHE_DIR / f"{h}.json"
        if not p.exists():
            return None
        if _time_cache.time() - p.stat().st_mtime > _PLACES_CACHE_TTL_SEC:
            return None
        data = _json_cache.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else None
    except Exception:
        return None


def _places_cache_set(chave: str, valor: list) -> None:
    try:
        _PLACES_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        h = hashlib.sha1(chave.encode("utf-8")).hexdigest()[:24]
        (_PLACES_CACHE_DIR / f"{h}.json").write_text(
            _json_cache.dumps(valor, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        pass


def _google_maps_error_denied(result: dict) -> bool:
    err = (result.get("error") or "").upper()
    detail = str(result.get("detail") or "").upper()
    return "REQUEST_DENIED" in err or "REQUEST_DENIED" in detail or "API_KEY" in detail


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
        out: dict = {
            "lat": loc["lat"],
            "lng": loc["lng"],
            "formatted_address": r["formatted_address"],
            "place_id": r.get("place_id", ""),
            "fonte_geocode": "google",
        }
        geom = r.get("geometry") or {}
        viewport = geom.get("viewport") or geom.get("bounds")
        if viewport and "northeast" in viewport and "southwest" in viewport:
            ne = viewport["northeast"]
            sw = viewport["southwest"]
            out["viewport"] = {
                "ne": {"lat": ne["lat"], "lng": ne["lng"]},
                "sw": {"lat": sw["lat"], "lng": sw["lng"]},
            }
        return out
    msg = data.get("error_message") or data.get("status")
    return {"error": f"Geocoding falhou: {data.get('status')}", "detail": msg}


def geocode_endereco(endereco: str) -> dict:
    """Converte endereço em lat/lng (Google → fallback Nominatim/OSM)."""
    result = _geocode_google(endereco)
    if "error" not in result:
        return result
    try:
        from tools.maps_fallback import fallback_habilitado, geocode_nominatim

        if fallback_habilitado() and _google_maps_error_denied(result):
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
        "google_maps_uri": p.get("googleMapsUri", ""),
        "tem_24h": tem_24h,
        "horarios": periodos[:3],
    }


def _raio_para_zoom(raio_metros: int) -> int:
    """raio (m) → nível de zoom do `ll` do SearchAPI google_maps."""
    if raio_metros <= 1500:
        return 15
    if raio_metros <= 3500:
        return 14
    if raio_metros <= 7000:
        return 13
    return 12


def _searchapi_maps_local(query: str, lat: float, lng: float, raio_metros: int,
                          *, tool_name: str, max_results: int = 20) -> list[dict] | None:
    """SearchAPI engine=google_maps com bias `ll` → adaptado p/ o shape places[] do
    Places API (consumível por _extrair_lugar). place_id é ChIJ... (idêntico). ~4× barato.
    None se sem key/erro → caller cai pro Places."""
    import os as _os

    key = (_os.getenv("SEARCHAPI_KEY") or "").strip()
    if not key:
        return None
    zoom = _raio_para_zoom(raio_metros)
    try:
        from tools.api_cost_tracker import track_api_call

        with track_api_call(tool_name, "searchapi_google_maps", 1):
            with httpx.Client(timeout=25) as c:
                data = c.get(
                    "https://www.searchapi.io/api/v1/search",
                    params={"engine": "google_maps", "q": query,
                            "ll": f"@{lat},{lng},{zoom}z", "gl": "br", "hl": "pt-br"},
                    headers={"Authorization": f"Bearer {key}"},
                ).json()
    except Exception as exc:
        logger.debug("searchapi google_maps local '%s': %s", query, exc)
        return None

    places: list[dict] = []
    for p in (data.get("local_results") or [])[:max_results]:
        gps = p.get("gps_coordinates") or {}
        horas = p.get("hours")
        pid = p.get("place_id") or ""
        places.append({
            "id": pid,
            "displayName": {"text": p.get("title") or ""},
            "formattedAddress": p.get("address") or "",
            "location": {"latitude": gps.get("latitude") or 0.0, "longitude": gps.get("longitude") or 0.0},
            "types": p.get("types") or ([p["type"]] if p.get("type") else []),
            "businessStatus": p.get("open_state") or "",
            "rating": p.get("rating"),
            "userRatingCount": p.get("reviews") or 0,
            "nationalPhoneNumber": p.get("phone") or "",
            "websiteUri": p.get("website") or "",
            "googleMapsUri": f"https://www.google.com/maps/place/?q=place_id:{pid}" if pid else "",
            "regularOpeningHours": {"weekdayDescriptions": [horas] if isinstance(horas, str) and horas else []},
        })
    return places


def _imoveis_backend_searchapi() -> bool:
    import os as _os
    return (_os.getenv("IMOVEIS_MAPS_BACKEND") or "searchapi").strip().lower() != "places"


def buscar_pontos_comerciais(latitude: float, longitude: float,
                              raio_metros: int = 5000) -> list[dict]:
    """Nearby Search por espaços comerciais candidatos."""
    cache_key = f"pontos:{latitude:.4f}:{longitude:.4f}:{raio_metros}"
    cached = _places_cache_get(cache_key)
    if cached is not None:
        return cached
    if _imoveis_backend_searchapi():
        res = _searchapi_maps_local(
            "shopping centro comercial supermercado mercado", latitude, longitude,
            raio_metros, tool_name="buscar_pontos_comerciais")
        if res:
            out = [_extrair_lugar(p) for p in res]
            _places_cache_set(cache_key, out)
            return out
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": get_google_maps_api_key(),
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,"
            "places.location,places.types,places.businessStatus,"
            "places.rating,places.userRatingCount,"
            # SEM contact data (phone/website/hours): esta busca traz ÂNCORAS/
            # polos (supermercado, shopping) — ninguém liga pro Carrefour pra
            # alugar ponto. Contact fica só em buscar_imoveis_texto (candidato
            # real, contato de imobiliária importa). Corta SKU Enterprise.
            "places.googleMapsUri"
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
        out = [_extrair_lugar(p) for p in data.get("places", [])]
        _places_cache_set(cache_key, out)
        return out

    if resp.status_code != 200:
        logger.warning(
            "Places Nearby falhou HTTP %s — sem fallback OSM (tipos comerciais ≠ academias)",
            resp.status_code,
        )
    return []


def buscar_imoveis_texto(query: str, latitude: float, longitude: float,
                          raio_metros: int = 5000) -> list[dict]:
    """Text Search para imóveis comerciais: 'galpão para alugar', etc."""
    cache_key = f"imoveis:{query.strip().lower()}:{latitude:.4f}:{longitude:.4f}:{raio_metros}"
    cached = _places_cache_get(cache_key)
    if cached is not None:
        return cached
    if _imoveis_backend_searchapi():
        res = _searchapi_maps_local(
            query, latitude, longitude, raio_metros, tool_name="buscar_imoveis_texto", max_results=10)
        if res:
            out = [_extrair_lugar(p) for p in res]
            _places_cache_set(cache_key, out)
            return out
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": get_google_maps_api_key(),
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,"
            "places.location,places.types,places.businessStatus,"
            "places.rating,places.userRatingCount,"
            # Contact mantido (telefone de imobiliária = lead do candidato);
            # regularOpeningHours cortado — imóvel vago não tem horário.
            "places.nationalPhoneNumber,places.websiteUri,"
            "places.googleMapsUri"
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
        out = [_extrair_lugar(p) for p in data.get("places", [])]
        _places_cache_set(cache_key, out)
        return out

    if resp.status_code != 200:
        logger.warning("Places Text Search falhou HTTP %s para: %s", resp.status_code, query[:80])
    return []


def obter_street_view_url(latitude: float, longitude: float,
                           width: int = 640, height: int = 400) -> str:
    """URL de imagem Street View — proxy da API por padrão (sem key no JSON)."""
    from tools.maps_street_view import (
        build_street_view_proxy_url,
        street_view_proxy_enabled,
    )

    if street_view_proxy_enabled():
        return build_street_view_proxy_url(latitude, longitude, width=width, height=height)
    return (
        f"{STREET_VIEW_BASE}?size={width}x{height}"
        f"&location={latitude},{longitude}&fov=90&key={get_google_maps_api_key()}"
    )


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


def obter_atributos_place(place_id: str) -> dict:
    """
    Atributos da aba Sobre (Places API New — SKU Enterprise + Atmosphere).

    Campos típicos: accessibilityOptions, paymentOptions, restroom, etc.
    Popular times NÃO está na API — continua via SearchAPI/Playwright.
    """
    if not get_google_maps_api_key() or not place_id:
        return {}
    headers = {
        "X-Goog-Api-Key": get_google_maps_api_key(),
        "X-Goog-FieldMask": (
            "id,accessibilityOptions,paymentOptions,restroom,"
            "goodForChildren,outdoorSeating"
        ),
    }
    from tools.api_cost_tracker import track_api_call

    with track_api_call("obter_atributos_place", "places_details_new", 1):
        try:
            with httpx.Client(timeout=12) as c:
                r = c.get(
                    f"{PLACES_BASE}/{place_id}",
                    headers=headers,
                    params={"languageCode": "pt-BR"},
                )
                if r.status_code != 200:
                    return {"erro": f"HTTP {r.status_code}"}
                data = r.json()
        except Exception as e:
            return {"erro": str(e)[:200]}

    acc = data.get("accessibilityOptions") or {}
    pay = data.get("paymentOptions") or {}
    return {
        "acessibilidade": {
            "banheiro_acessivel_cadeira": acc.get("wheelchairAccessibleRestroom"),
            "entrada_acessivel": acc.get("wheelchairAccessibleEntrance"),
            "estacionamento_acessivel": acc.get("wheelchairAccessibleParking"),
        },
        "pagamentos": {
            "cartao_credito": pay.get("acceptsCreditCards"),
            "cartao_debito": pay.get("acceptsDebitCards"),
            "nfc": pay.get("acceptsNfc"),
            "dinheiro": pay.get("acceptsCashOnly") is False,
        },
        "comodidades": {
            "banheiro": data.get("restroom"),
        },
        "opcoes_servico": {},
        "fonte": "places_api_new",
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
