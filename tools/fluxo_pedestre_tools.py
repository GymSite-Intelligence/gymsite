"""Integração fluxo pedestre — relatório, candidatos A1, API."""
from __future__ import annotations

import logging
from typing import Any

from tools.space_syntax import (
    AnalysisConfig,
    calculate_natural_movement,
    generate_context_for_rag,
    score_candidate_flow,
    unavailable_flow_result,
)
from tools.spatial_flow_cache import get_cached_flow, set_cached_flow

logger = logging.getLogger(__name__)


def run_flow_analysis(
    lat: float,
    lng: float,
    *,
    radius_m: int = 2000,
    competidores: list[dict] | None = None,
    custom_pois: list[dict] | None = None,
    use_cache: bool = True,
) -> dict[str, Any]:
    if use_cache:
        cached = get_cached_flow(lat, lng, radius_m)
        if cached:
            cached["from_cache"] = True
            return cached
    config = AnalysisConfig(radius_meters=radius_m, network_type="walk")
    try:
        result = calculate_natural_movement(
            lat,
            lng,
            config=config,
            custom_pois=custom_pois,
            competidores=competidores,
        )
    except Exception as exc:
        logger.error("fluxo pedestre falhou: %s", exc)
        return unavailable_flow_result(str(exc))
    if result.get("success"):
        set_cached_flow(lat, lng, radius_m, result)
    return result


def enrich_candidato_fluxo(
    candidato: dict,
    *,
    competidores: list[dict] | None = None,
    radius_m: int = 2000,
) -> dict:
    lat = candidato.get("lat")
    lng = candidato.get("lng")
    if lat is None or lng is None:
        candidato["fluxo_confianca"] = "indisponivel"
        candidato["fluxo_score"] = None
        return candidato
    try:
        analysis = run_flow_analysis(
            float(lat),
            float(lng),
            radius_m=radius_m,
            competidores=competidores,
        )
        if not analysis.get("success"):
            candidato["fluxo_confianca"] = "indisponivel"
            candidato["fluxo_motivo"] = analysis.get("motivo", "análise indisponível")
            return candidato
        scored = score_candidate_flow(float(lat), float(lng), analysis, radius_m)
        candidato.update(scored)
    except Exception as exc:
        logger.warning("enrich_candidato_fluxo: %s", exc)
        candidato["fluxo_confianca"] = "indisponivel"
    return candidato


def build_fluxo_pedestre_block(
    lat: float,
    lng: float,
    *,
    competidores: list[dict] | None = None,
    radius_m: int = 2000,
    location_name: str = "",
) -> dict[str, Any]:
    analysis = run_flow_analysis(lat, lng, radius_m=radius_m, competidores=competidores)
    if not analysis.get("success"):
        return {
            "confianca": "indisponivel",
            "motivo": analysis.get("motivo", "malha OSM indisponível"),
            "leitura": "",
        }
    scored = score_candidate_flow(lat, lng, analysis, radius_m)
    stats = analysis.get("statistics") or {}
    return {
        "confianca": scored.get("fluxo_confianca", "media"),
        "fluxo_score": scored.get("fluxo_score"),
        "fluxo_norm": scored.get("fluxo_norm"),
        "fluxo_segmento": scored.get("fluxo_segmento"),
        "carimbo": scored.get("fluxo_carimbo"),
        "statistics": stats,
        "top_segments": (analysis.get("top_segments") or [])[:5],
        "leitura": generate_context_for_rag(analysis, location_name or "o ponto analisado"),
        "attribution": "© OpenStreetMap contributors",
    }


def build_fluxo_payload_for_relatorio(
    *,
    lat: float | None,
    lng: float | None,
    competidores: list[dict] | None = None,
    radius_m: int = 2000,
    candidato_lat: float | None = None,
    candidato_lng: float | None = None,
) -> dict[str, Any]:
    if lat is None or lng is None:
        return unavailable_flow_result("coordenadas ausentes no relatório")
    analysis = run_flow_analysis(
        float(lat),
        float(lng),
        radius_m=radius_m,
        competidores=competidores,
    )
    if not analysis.get("success"):
        return analysis
    clat = candidato_lat if candidato_lat is not None else lat
    clng = candidato_lng if candidato_lng is not None else lng
    scored = score_candidate_flow(float(clat), float(clng), analysis, radius_m)
    return {
        "success": True,
        "confianca": scored.get("fluxo_confianca"),
        "fluxo_score_candidato": scored.get("fluxo_score"),
        "carimbo": scored.get("fluxo_carimbo"),
        "statistics": analysis.get("statistics"),
        "geojson": analysis.get("geojson"),
        "top_segments": analysis.get("top_segments"),
        "attribution": "© OpenStreetMap contributors",
        "from_cache": analysis.get("from_cache", False),
    }
