"""
Validação de segmento via Google Places (opcional).

Usar só para registros com confiança baixa/média — evita 1.800+ chamadas no parque inteiro.
Ativar: CNPJ_SEGMENT_PLACES_VALIDATE=1
"""

from __future__ import annotations

import os
import re
from typing import Any

from tools.cnpj_segment_classifier import ClassificacaoSegmento, classificar_segmento
from tools.google_maps_key import get_google_maps_api_key

PLACES_BASE = "https://places.googleapis.com/v1/places"

# Cache em memória por processo (endereco+nome)
_CACHE: dict[str, ClassificacaoSegmento] = {}


def _norm_key(*parts: str) -> str:
    return "|".join(re.sub(r"\s+", " ", (p or "").strip().lower()) for p in parts)


def _segmento_from_place(nome: str, tipos: list[str]) -> tuple[str, list[str]]:
    n = (nome or "").lower()
    types = {str(t).lower() for t in tipos if t}
    sinais: list[str] = []

    if any(t in types for t in ("physiotherapist", "doctor", "hospital", "medical_center")):
        return "saude_clinica", ["places:type saude"]

    base = classificar_segmento(nome)
    seg = base.segmento
    sinais.extend(base.sinais)

    if "gym" in types or "fitness_center" in types:
        sinais.append("places:type gym")
        if seg in ("academia", "studio_bem_estar", "lutas"):
            return seg, sinais
        return "academia", sinais

    if "sports_club" in types and seg == "academia":
        sinais.append("places:sports_club")
    return seg, sinais


def validar_segmento_places(
    nome_fantasia: str | None,
    *,
    endereco: str | None = None,
    cidade: str = "",
    uf: str = "",
) -> ClassificacaoSegmento | None:
    """
    Busca o estabelecimento no Google Places e refina o segmento.
    Retorna None se API indisponível ou sem match.
    """
    if os.getenv("CNPJ_SEGMENT_PLACES_VALIDATE", "").strip() not in ("1", "true", "yes"):
        return None
    if not get_google_maps_api_key():
        return None

    nome = (nome_fantasia or "").strip()
    if not nome and not endereco:
        return None

    cache_key = _norm_key(nome, endereco or "", cidade)
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    import httpx

    q_parts = [p for p in (nome or "academia", endereco, cidade, uf) if p]
    text_query = ", ".join(q_parts)

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": get_google_maps_api_key(),
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,places.types"
        ),
    }
    body = {
        "textQuery": text_query,
        "maxResultCount": 3,
        "languageCode": "pt-BR",
        "regionCode": "BR",
    }

    try:
        with httpx.Client(timeout=12) as client:
            data = client.post(
                f"{PLACES_BASE}:searchText", json=body, headers=headers
            ).json()
    except Exception:
        return None

    places = data.get("places") or []
    if not places:
        return None

    p0 = places[0]
    nome_place = (p0.get("displayName") or {}).get("text", "") or nome
    tipos = p0.get("types") or []
    seg, sinais = _segmento_from_place(nome_place, tipos)

    result = ClassificacaoSegmento(
        segmento=seg,
        confianca="alta",
        metodo="places",
        sinais=sinais + [f"places:{nome_place[:60]}"],
        requer_validacao=False,
        incluir_no_parque=seg != "saude_clinica",
    )
    _CACHE[cache_key] = result
    return result


def refinar_classificacao(
    base: ClassificacaoSegmento,
    *,
    nome_fantasia: str | None,
    endereco: str | None = None,
    cidade: str = "",
    uf: str = "",
    force: bool = False,
) -> ClassificacaoSegmento:
    """
    Places quando force=True (lista de entrantes) ou heurística incerta.
    """
    if not force and base.confianca == "alta" and base.metodo != "default_mercado":
        return base
    places = validar_segmento_places(
        nome_fantasia, endereco=endereco, cidade=cidade, uf=uf
    )
    return places or base
