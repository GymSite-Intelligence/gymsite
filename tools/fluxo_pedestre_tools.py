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


# ── Top vias por fluxo (prospecção sem imóvel real) ──────────────────────────

_TIPO_VIA_PREFIXOS = (
    ("avenida", "avenida"),
    ("av.", "avenida"),
    ("av ", "avenida"),
    ("alameda", "avenida"),
    ("rodovia", "avenida"),
    ("travessa", "travessa"),
    ("trav.", "travessa"),
    ("rua", "rua"),
    ("r.", "rua"),
    ("r ", "rua"),
    ("largo", "rua"),
    ("praça", "rua"),
    ("praca", "rua"),
)


def _classificar_tipo_via(nome: str) -> str:
    low = (nome or "").strip().lower()
    for prefixo, tipo in _TIPO_VIA_PREFIXOS:
        if low.startswith(prefixo):
            return tipo
    return "rua"


def _normalize_street_name(raw) -> str:
    """OSM/osmnx às vezes entrega ``name`` como lista (múltiplos nomes no way).

    Preferimos avenida/av. quando houver; senão o primeiro token não-vazio.
    Nunca serializa lista com ``str([...])`` — isso virava chave falsa no ranking.
    """
    if raw is None:
        return ""
    if isinstance(raw, (list, tuple, set)):
        names = [str(x).strip() for x in raw if str(x).strip()]
    else:
        s = str(raw).strip()
        if not s:
            return ""
        # Fallback: lista já stringificada no geojson/cache legado
        if s.startswith("[") and s.endswith("]"):
            try:
                import ast

                parsed = ast.literal_eval(s)
                if isinstance(parsed, (list, tuple)):
                    names = [str(x).strip() for x in parsed if str(x).strip()]
                else:
                    return s
            except (SyntaxError, ValueError, MemoryError):
                return s
        else:
            return s
    if not names:
        return ""
    for n in names:
        low = n.lower()
        if low.startswith(("avenida ", "av. ", "av ")):
            return n
    return names[0]


def _agregar_features_por_via(features: list[dict]) -> dict[str, dict]:
    """Agrega flow_score do GeoJSON (já calculado) por street_name.

    Ranking = score máximo do segmento (alinha com ``top_segments``); média
    simples diluía artérias longas e elevava vielas/trilhas com poucos trechos.
    """
    vias: dict[str, dict] = {}
    for feat in features:
        if not isinstance(feat, dict):
            continue
        props = feat.get("properties") or {}
        if not isinstance(props, dict):
            continue
        nome = _normalize_street_name(props.get("street_name"))
        if not nome:
            continue
        # Trilha/path não é via de prospecção comercial
        hw = str(props.get("highway_type") or props.get("highway") or "").lower()
        if hw in {"path", "footway", "steps", "bridleway", "corridor"}:
            continue
        if nome.lower().startswith("trilha"):
            continue
        score = props.get("flow_score")
        try:
            score_f = float(score)
        except (TypeError, ValueError):
            continue
        if score_f > 1.0:
            score_f = score_f / 100.0
        length = props.get("length_meters") or 0
        try:
            length_f = float(length)
        except (TypeError, ValueError):
            length_f = 0.0
        # length absurdo (CRS/unidade) — não contamina trecho
        if length_f < 0 or length_f > 5_000:
            length_f = 0.0
        bucket = vias.setdefault(
            nome,
            {
                "score_sum": 0.0,
                "score_max": 0.0,
                "n_segments": 0,
                "length_m": 0.0,
                "tipo_via": _classificar_tipo_via(nome),
            },
        )
        bucket["score_sum"] += score_f
        bucket["score_max"] = max(float(bucket["score_max"]), score_f)
        bucket["n_segments"] += 1
        bucket["length_m"] += length_f
    for bucket in vias.values():
        n = max(int(bucket["n_segments"]), 1)
        bucket["score_medio"] = float(bucket["score_sum"]) / n
        # score usado no ranking/display
        bucket["score_rank"] = float(bucket["score_max"])
    return vias


def _contar_concorrentes_por_via(
    vias: dict[str, dict],
    competidores: list[dict] | None,
) -> dict[str, int]:
    """Best-effort: match frouxo do nome da via no endereço do concorrente."""
    contagem: dict[str, int] = {}
    if not competidores:
        return contagem
    for c in competidores:
        if not isinstance(c, dict):
            continue
        end = str(c.get("endereco") or c.get("address") or "").lower()
        if not end:
            continue
        for nome in vias:
            token = nome.lower()
            # Evita match curto demais (ex.: "Rua")
            if len(token) < 8:
                continue
            if token in end or token.replace("avenida ", "av. ") in end:
                contagem[nome] = contagem.get(nome, 0) + 1
                break
    return contagem


def top_vias_por_fluxo(
    lat: float,
    lng: float,
    *,
    top_n: int = 5,
    radius_m: int = 2000,
    competidores: list | None = None,
    bairro: str = "",
) -> dict:
    """Guia de prospecção: top vias por fluxo estrutural (agregado por nome).

    Reusa ``run_flow_analysis`` / motor angular já existente (cache espacial).
    Fail-soft: nunca inventa scores.
    """
    try:
        analysis = run_flow_analysis(
            float(lat),
            float(lng),
            radius_m=int(radius_m),
            competidores=list(competidores or []) if competidores else None,
        )
    except Exception as exc:
        logger.warning("top_vias_por_fluxo: análise falhou: %s", exc)
        return {
            "status": "indisponivel",
            "motivo": f"{type(exc).__name__}: {exc}",
            "top_vias": [],
            "confianca": "indisponivel",
        }

    if not analysis.get("success"):
        return {
            "status": "indisponivel",
            "motivo": analysis.get("motivo", "malha OSM indisponível"),
            "top_vias": [],
            "confianca": "indisponivel",
        }

    geojson = analysis.get("geojson") or {}
    features = geojson.get("features") if isinstance(geojson, dict) else None
    if not isinstance(features, list) or not features:
        # Fallback: top_segments já ranqueados (sem agregação completa)
        segs = analysis.get("top_segments") or []
        top_vias_out = []
        for i, seg in enumerate(segs[:top_n]):
            if not isinstance(seg, dict):
                continue
            nome = _normalize_street_name(seg.get("street_name")) or f"Segmento #{i + 1}"
            raw = seg.get("flow_score")
            try:
                score_01 = float(raw)
            except (TypeError, ValueError):
                continue
            if score_01 > 1.0:
                score_01 = score_01 / 100.0
            score_100 = round(score_01 * 100)
            top_vias_out.append(
                {
                    "nome_via": nome,
                    "tipo_via": _classificar_tipo_via(nome),
                    "fluxo_score": score_100,
                    "fluxo_norm": round(score_01, 4),
                    "trecho": "—",
                    "concorrentes_no_trecho": 0,
                    "ancoras_proximas": [],
                    "fluxo_carimbo": {
                        "valor": score_100,
                        "base": f"top_segments · raio {radius_m}m",
                        "fonte": "OSM malha viária + sintaxe espacial angular",
                        "janela": "malha estática · censo 2022",
                        "metodo": "angular segment analysis (fallback top_segments)",
                    },
                }
            )
        if not top_vias_out:
            return {
                "status": "indisponivel",
                "motivo": "geojson/top_segments vazios",
                "top_vias": [],
                "confianca": "indisponivel",
            }
        stats = analysis.get("statistics") or {}
        mapa_svg = None
        try:
            from tools.vias_geometry_tools import anexar_geometria_e_mapa

            mapa_svg = anexar_geometria_e_mapa(
                top_vias_out, list(features) if isinstance(features, list) else None, lat, lng
            )
        except Exception:
            logger.warning("top_vias mapa_svg (fallback) falhou", exc_info=True)
        return {
            "status": "ok",
            "top_vias": top_vias_out,
            "confianca": analysis.get("confianca") or "media",
            "total_segments": stats.get("total_segments"),
            "mean_flow_score": stats.get("mean_flow_score"),
            "bairro": bairro,
            "mapa_svg": mapa_svg,
            "recomendacao": (
                "Validar in loco disponibilidade de imóvel comercial nestas vias "
                "antes de fechar negociação."
            ),
        }

    vias = _agregar_features_por_via(features)
    if not vias:
        return {
            "status": "indisponivel",
            "motivo": "nenhuma via com nome na malha",
            "top_vias": [],
            "confianca": "indisponivel",
        }

    ranked = sorted(
        vias.items(),
        key=lambda kv: (kv[1].get("score_rank", 0.0), kv[1].get("length_m", 0.0)),
        reverse=True,
    )
    conc_por_via = _contar_concorrentes_por_via(vias, list(competidores or []))
    stats = analysis.get("statistics") or {}
    n_seg = int(stats.get("total_segments") or len(features) or 0)
    if n_seg >= 100:
        confianca = "alta"
    elif n_seg >= 30:
        confianca = "media"
    else:
        confianca = "baixa"

    top_vias_out = []
    for nome_via, v_data in ranked[: max(1, int(top_n))]:
        score_01 = float(v_data.get("score_rank") or v_data["score_medio"])
        score_100 = round(score_01 * 100)
        length_m = float(v_data.get("length_m") or 0.0)
        # Cap visual: soma > 20 km quase sempre é artefato de unidade/duplicata
        if 0 < length_m <= 20_000:
            trecho = f"~{int(length_m)} m"
        else:
            trecho = "—"
        top_vias_out.append(
            {
                "nome_via": nome_via,
                "tipo_via": v_data["tipo_via"],
                "fluxo_score": score_100,
                "fluxo_norm": round(score_01, 4),
                "trecho": trecho,
                "concorrentes_no_trecho": conc_por_via.get(nome_via, 0),
                "ancoras_proximas": [],
                "fluxo_carimbo": {
                    "valor": score_100,
                    "base": f"segmentos OSM · raio {radius_m}m · agregado por via",
                    "fonte": "OSM malha viária + sintaxe espacial angular",
                    "janela": "malha estática · censo 2022",
                    "metodo": (
                        "angular segment analysis (Choice+Integration); "
                        "score = max do segmento na via"
                    ),
                },
            }
        )

    mapa_svg = None
    try:
        from tools.vias_geometry_tools import anexar_geometria_e_mapa

        mapa_svg = anexar_geometria_e_mapa(top_vias_out, features, lat, lng)
    except Exception:
        logger.warning("top_vias mapa_svg falhou", exc_info=True)

    return {
        "status": "ok",
        "top_vias": top_vias_out,
        "confianca": confianca,
        "total_segments": n_seg,
        "mean_flow_score": round(float(stats.get("mean_flow_score") or 0.0), 4),
        "bairro": bairro,
        "mapa_svg": mapa_svg,
        "recomendacao": (
            "Validar in loco disponibilidade de imóvel comercial nestas vias "
            "antes de fechar negociação. O fluxo estrutural indica prioridade "
            "de prospecção, não garante imóvel disponível."
        ),
    }
