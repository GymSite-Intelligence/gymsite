"""
Anéis competitivos (Apêndice D do Motor v2) — corrige o score competitivo distorcido
pelo vizinho (caso Wally/Cocó: 40 pins, 7 listados de OUTROS bairros).

Classifica cada concorrente em anel pela distância à área-alvo, pondera o score:
  NO_BAIRRO  (dentro/mesmo bairro)  peso 1.00 — quem disputa o aluno que mora AQUI
  FRONTEIRA  (≤ raio da borda)      peso 0.50 — pra onde o aluno atravessa
  REGIONAL   (resto do raio)        peso 0.20 — benchmark de preço/posicionamento

V1 sem polígono: anel por NOME do bairro (match) + distância ao centroide (proxy da
borda). Porte por nº de avaliações; multiesporte (gym + termo aquático/luta) é flag,
não exclusão (evita falso negativo tipo Club Cocó).

Regra de ouro: pesos/raio/limiares vêm de parametros_metodologia (recalibrável).
"""
from __future__ import annotations

import re
from typing import Any

from tools.bairro_normalize import normalizar_bairro
from tools.parametros_metodologia import param

_AQUATICO = ("nataç", "natac", "hidro", "aqua", "piscina", "swim")
_LUTA = ("luta", "jiu", "muay", "boxe", " box", "karate", "judo", "taekwondo", "mma",
         "krav", "capoeira", "wrestling", "kung")


def _coord(c: dict, k: str) -> float | None:
    try:
        v = c.get(k)
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def classificar_anel(
    comp: dict, bairro_alvo: str, centroid_lat: float | None, centroid_lng: float | None
) -> tuple[str, float, float | None]:
    """(anel, peso, dist_km). NO_BAIRRO por nome; senão por distância ao centroide."""
    dist = None
    lat, lng = _coord(comp, "lat"), _coord(comp, "lng")
    if centroid_lat is not None and centroid_lng is not None and lat is not None and lng is not None:
        from tools.maps_tools import calcular_distancia_km

        dist = calcular_distancia_km(centroid_lat, centroid_lng, lat, lng)

    # Campo do concorrente é `bairro_concorrente` (de _aplicar_bairro_concorrente);
    # `bairro` é fallback. Match por CONTÉM (endereço vem "Lojas 2/3 - Cocó", não só "Cocó").
    bairro_c = comp.get("bairro_concorrente") or comp.get("bairro") or ""
    alvo_n = normalizar_bairro(bairro_alvo or "")
    comp_n = normalizar_bairro(bairro_c)
    if alvo_n and comp_n and (alvo_n == comp_n or alvo_n in comp_n):
        return "NO_BAIRRO", param("anel_peso_no_bairro"), dist
    if dist is not None and dist <= param("raio_fronteira_km"):
        return "FRONTEIRA", param("anel_peso_fronteira"), dist
    # sem coords e sem match de bairro → REGIONAL (conservador, não infla o bairro)
    return "REGIONAL", param("anel_peso_regional"), dist


def classificar_porte(num_avaliacoes: Any) -> str:
    try:
        n = int(num_avaliacoes or 0)
    except (TypeError, ValueError):
        n = 0
    if n <= param("porte_pequena_max_avaliacoes"):
        return "pequena"
    if n <= param("porte_media_max_avaliacoes"):
        return "media"
    return "grande"


def eh_multiesporte(comp: dict) -> bool:
    """gym + termo aquático/luta no nome → clube multiesporte (flag, não exclusão)."""
    tipos = [str(t).lower() for t in (comp.get("tipos") or [])]
    if not any("gym" in t or "academ" in t for t in tipos):
        return False
    nome = (comp.get("nome") or "").lower()
    return any(k in nome for k in _AQUATICO) or any(k in nome for k in _LUTA)


def enriquecer_competidores_aneis(
    competidores: list[dict], bairro_alvo: str,
    centroid_lat: float | None = None, centroid_lng: float | None = None,
) -> list[dict]:
    """Adiciona anel/peso_anel/dist_borda_km/porte/multiesporte a cada concorrente."""
    out = []
    for c in competidores or []:
        if not isinstance(c, dict):
            continue
        anel, peso, dist = classificar_anel(c, bairro_alvo, centroid_lat, centroid_lng)
        out.append({
            **c,
            "anel": anel,
            "peso_anel": peso,
            "dist_borda_km": round(dist, 2) if dist is not None else None,
            "porte": classificar_porte(c.get("num_avaliacoes")),
            "multiesporte": eh_multiesporte(c),
        })
    return out


def resumo_aneis(competidores_enriquecidos: list[dict]) -> dict[str, Any]:
    """Score competitivo PONDERADO por anel + contagens honestas (não lista plana)."""
    por_anel: dict[str, int] = {"NO_BAIRRO": 0, "FRONTEIRA": 0, "REGIONAL": 0}
    score = 0.0
    no_bairro_portes: dict[str, int] = {"pequena": 0, "media": 0, "grande": 0}
    for c in competidores_enriquecidos or []:
        anel = c.get("anel") or "REGIONAL"
        por_anel[anel] = por_anel.get(anel, 0) + 1
        score += float(c.get("peso_anel") or 0)
        if anel == "NO_BAIRRO":
            no_bairro_portes[c.get("porte") or "pequena"] = no_bairro_portes.get(c.get("porte") or "pequena", 0) + 1
    return {
        "por_anel": por_anel,
        "score_competitivo_ponderado": round(score, 2),
        "concorrentes_no_bairro": por_anel["NO_BAIRRO"],
        "no_bairro_por_porte": no_bairro_portes,
        "total_concorrentes": sum(por_anel.values()),
        "nota": ("Score ponderado por anel: NO_BAIRRO peso 1.0, FRONTEIRA 0.5, REGIONAL 0.2. "
                 "'2 tradicionais no anel do bairro' ≠ '7 concorrentes' (Apêndice D)."),
    }
