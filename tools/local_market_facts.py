"""
Fatos locais verificáveis (Nominatim + Overpass) — complementam Deep Research.

Não substitui CNJ (cartório). Uso: competição no raio, geocode do bairro, marcas OSM.
"""
from __future__ import annotations

from typing import Any

# (padrão no nome, label exibição)
_MARCAS_FITNESS: list[tuple[str, str]] = [
    ("smart fit", "Smart Fit"),
    ("smartfit", "Smart Fit"),
    ("selfit", "Selfit"),
    ("greenlife", "Greenlife"),
    ("top up", "Top Up"),
    ("gaviões", "Gaviões"),
    ("gavioes", "Gaviões"),
    ("ironberg", "Ironberg"),
    ("ayo fitness", "Ayo Fitness Club"),
    ("bluefit", "Bluefit"),
    ("bodytech", "Bodytech"),
    ("pratique fitness", "Pratique Fitness"),
    ("velocity", "Velocity"),
    ("live!", "Live!"),
    ("live ", "Live!"),
    ("panobianco", "Panobianco"),
    ("fitness club", "Fitness Club"),
    ("world gym", "World Gym"),
    ("gaviões academia", "Gaviões"),
]


def inferir_redes_de_concorrentes(concorrentes: list[dict]) -> list[str]:
    """Extrai marcas reconhecíveis a partir dos nomes das unidades (OSM/Places)."""
    found: list[str] = []
    seen: set[str] = set()
    for c in concorrentes:
        nome = (c.get("nome") or "").lower()
        if not nome:
            continue
        for pattern, label in _MARCAS_FITNESS:
            if pattern in nome and label not in seen:
                seen.add(label)
                found.append(label)
    return found


def fatos_competicao_local(
    cidade: str,
    bairro: str = "",
    uf: str = "CE",
    raio_metros: int = 5000,
    limit: int = 25,
) -> dict[str, Any]:
    """
    Tool A0 — fatos de competição no raio via geocode + Overpass (sem Google Places).

    Retorna apenas dados observados; não lista redes do DR.
    """
    from tools.maps_fallback import fallback_habilitado, geocode_nominatim, overpass_fitness_near
    from tools.maps_tools import _geocode_google, calcular_distancia_km

    endereco = f"{bairro}, {cidade}, {uf}, Brasil".strip(", ") if bairro else f"{cidade}, {uf}, Brasil"
    geo = _geocode_google(endereco)
    if "error" in geo:
        if fallback_habilitado():
            geo = geocode_nominatim(endereco)
        if "error" in geo:
            return {
                "status": "erro",
                "motivo": geo.get("error"),
                "endereco_consultado": endereco,
            }

    lat, lng = geo["lat"], geo["lng"]
    fb = overpass_fitness_near(lat, lng, raio_metros, limit=limit)
    places = fb.get("places") or []
    concorrentes = []
    for p in places:
        plat, plng = p.get("lat", 0), p.get("lng", 0)
        concorrentes.append(
            {
                "nome": p.get("nome"),
                "endereco": p.get("endereco"),
                "distancia_km": round(calcular_distancia_km(lat, lng, plat, plng), 2),
                "fonte": "overpass_osm",
            }
        )
    redes = inferir_redes_de_concorrentes(
        [{"nome": c.get("nome")} for c in concorrentes]
    )
    return {
        "status": "ok",
        "cidade": cidade,
        "bairro": bairro or None,
        "uf": uf,
        "raio_metros": raio_metros,
        "fonte_geocode": geo.get("fonte_geocode", "google"),
        "lat_centro": lat,
        "lng_centro": lng,
        "total_unidades_osm": len(concorrentes),
        "redes_detectadas_osm": redes,
        "amostra_unidades": concorrentes[:15],
        "nota": (
            "Marcas inferidas por nome nas unidades OSM no raio. "
            "Independentes sem marca no nome não entram em redes_detectadas_osm."
        ),
    }
