"""
places_autocomplete.py — Proxy server-side para Google Places API (New) :autocomplete.

Usado pelo frontend em POST /api/places-autocomplete (bairros por município).
Chave server-side: GOOGLE_MAPS_API_KEY (ver tools/google_maps_key.py).
"""
from __future__ import annotations

import logging
import unicodedata
from typing import Any, Optional

import httpx

from tools.google_maps_key import get_google_maps_api_key

logger = logging.getLogger(__name__)

_PLACES_URL = "https://places.googleapis.com/v1/places:autocomplete"
_FIELD_MASK = (
    "suggestions.placePrediction.placeId,"
    "suggestions.placePrediction.text,"
    "suggestions.placePrediction.structuredFormat"
)


def _normalize(s: str) -> str:
    decomposed = unicodedata.normalize("NFD", s)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn").lower()


def _matches_municipio(
    contexto: str,
    texto_completo: str,
    municipio_norm: str,
    uf_norm: str,
) -> bool:
    """Aceita sugestão se o município aparece no contexto ou no texto completo."""
    if not municipio_norm:
        return True
    full = _normalize(f"{contexto} {texto_completo}")
    if municipio_norm not in full:
        return False
    # UF é hint extra; Places costuma retornar "Ceará" em vez de "CE".
    if uf_norm and len(uf_norm) == 2 and uf_norm not in full:
        return True
    return True


def _places_http_error(status_code: int, detail: str) -> str:
    """Mensagem amigável para 401/403 da Places API (New)."""
    detail_norm = (detail or "").lower()
    if status_code in (401, 403):
        if "api_key_service_blocked" in detail_norm or "are blocked" in detail_norm:
            return (
                "API key bloqueada para Places API (New): em Credentials, edite a chave e "
                "inclua Places API (New) em API restrictions (ou use None para dev)."
            )
        if (
            "places api (new) has not been used" in detail_norm
            or (
                "places.googleapis.com" in detail_norm
                and "disabled" in detail_norm
            )
        ):
            return (
                "Places API (New) nao habilitada no projeto Google Cloud: "
                "APIs & Services > Places API (New), billing ativo, aguarde ~5 min."
            )
        if "request_denied" in detail_norm:
            return (
                f"REQUEST_DENIED ({status_code}): verifique GOOGLE_MAPS_API_KEY, "
                "billing e APIs (Places API New + Geocoding)."
            )
        return (
            f"Places API retornou {status_code}: verifique GOOGLE_MAPS_API_KEY, "
            "billing e Places API (New) habilitada."
        )
    return f"Places API retornou {status_code}"


def places_autocomplete(
    input_text: str,
    municipio: str = "",
    uf: str = "",
    lat: Optional[float] = None,
    lng: Optional[float] = None,
) -> dict[str, Any]:
    """
    Retorna {"suggestions": [...]} ou {"suggestions": [], "error": "..."}.
    Contrato espelha o middleware Vite (frontend/vite.config.ts).
    """
    api_key = get_google_maps_api_key()
    if not api_key:
        return {
            "suggestions": [],
            "error": "GOOGLE_MAPS_API_KEY não configurada no servidor",
        }

    min_chars = 1 if municipio else 2
    if not input_text or len(input_text) < min_chars:
        return {"suggestions": []}

    query_string = (
        f"{municipio}{f' {uf}' if uf else ''}, {input_text}".strip()
        if municipio
        else input_text
    )
    params: dict[str, Any] = {
        "input": query_string,
        "languageCode": "pt-BR",
        "regionCode": "BR",
        "includedPrimaryTypes": ["sublocality", "neighborhood"],
    }
    if lat is not None and lng is not None:
        params["locationBias"] = {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": 15000.0,
            },
        }

    try:
        with httpx.Client(timeout=20.0) as client:
            upstream = client.post(
                _PLACES_URL,
                headers={
                    "content-type": "application/json",
                    "x-goog-api-key": api_key,
                    "x-goog-fieldmask": _FIELD_MASK,
                },
                json=params,
            )
    except httpx.HTTPError as exc:
        logger.warning("Places autocomplete HTTP error: %s", exc)
        return {"suggestions": [], "error": str(exc)}

    if upstream.status_code != 200:
        detail = upstream.text[:500]
        logger.warning(
            "Places autocomplete status=%s query=%r detail=%s",
            upstream.status_code,
            query_string,
            detail,
        )
        if upstream.status_code in (401, 403, 404, 429):
            return {
                "suggestions": [],
                "error": _places_http_error(upstream.status_code, detail),
            }
        return {
            "suggestions": [],
            "error": _places_http_error(upstream.status_code, detail),
        }

    data = upstream.json()
    municipio_norm = _normalize(municipio or "")
    uf_norm = _normalize(uf or "")

    suggestions: list[dict[str, str]] = []
    for raw in data.get("suggestions") or []:
        pred = raw.get("placePrediction") or {}
        main = (pred.get("structuredFormat") or {}).get("mainText", {}).get("text", "")
        secondary = (pred.get("structuredFormat") or {}).get("secondaryText", {}).get(
            "text", ""
        )
        texto_completo = (pred.get("text") or {}).get("text", "") or f"{main}, {secondary}"
        if not main:
            continue
        if not _matches_municipio(secondary, texto_completo, municipio_norm, uf_norm):
            continue
        suggestions.append(
            {
                "placeId": pred.get("placeId") or "",
                "bairro": main,
                "contexto": secondary,
                "textoCompleto": texto_completo,
            }
        )

    logger.info(
        "places_autocomplete query=%r kept=%d/%d",
        query_string,
        len(suggestions),
        len(data.get("suggestions") or []),
    )
    return {"suggestions": suggestions}
