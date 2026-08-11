"""ZEUS Fase 1 — proxy OSM (uso observado, nunca permissão legal).

Consulta Overpass (landuse + zoning) → classifica rótulo empírico →
compatibilidade sempre INDIVIDUALIZAR. Heurística de completude marca
baixa confiança quando a amostra no raio é esparsa.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("gymsite.zeus_osm")

# Rótulos de USO OBSERVADO — nunca PERMISSIVO/CONDICIONADO/RESTRITO.
_DEFAULT_USO_OBS = {
    "commercial": "comercial_observado",
    "retail": "comercial_observado",
    "industrial": "industrial_observado",
    "residential": "residencial_observado",
    "railway": "infraestrutura_observada",
    "military": "institucional_observado",
    "cemetery": "institucional_observado",
    "religious": "institucional_observado",
    "education": "institucional_observado",
    "hospital": "institucional_observado",
    "grass": "area_verde_observada",
    "forest": "area_verde_observada",
    "meadow": "area_verde_observada",
    "farmland": "rural_observado",
    "farmyard": "rural_observado",
    "orchard": "rural_observado",
    "construction": "em_transformacao_observado",
    "brownfield": "em_transformacao_observado",
    "recreation_ground": "lazer_observado",
    "village_green": "lazer_observado",
}


def _mapa_uso_observado() -> dict[str, str]:
    """Catálogo zoneamento_osm_uso_obs quando disponível; senão default auditável."""
    try:
        from tools.catalogos import catalogo_map

        m = catalogo_map("zoneamento_osm_uso_obs")
        if m:
            return {str(k).lower(): str(v) for k, v in m.items()}
    except Exception:
        pass
    return dict(_DEFAULT_USO_OBS)


def _params_completude() -> tuple[int, int, int, int]:
    """(raio_m, min_features_ok, confianca_alta, confianca_baixa)."""
    try:
        from tools.parametros_metodologia import param

        raio = int(param("zeus_osm_raio_m") or 150)
        min_ok = int(param("zeus_osm_completude_min_features") or 3)
        conf_alta = int(param("zeus_osm_confianca_alta") or 85)
        conf_baixa = int(param("zeus_osm_confianca_baixa") or 40)
    except Exception:
        raio, min_ok, conf_alta, conf_baixa = 150, 3, 85, 40
    return max(50, min(raio, 500)), max(1, min_ok), conf_alta, conf_baixa


def rotular_uso_observado(tag: str) -> str:
    """Tag OSM → rótulo empírico. Nunca vira veredito legal."""
    key = (tag or "").strip().lower()
    return _mapa_uso_observado().get(key, f"uso_observado_{key}" if key else "uso_observado_indefinido")


def avaliar_completude(n_features: int) -> dict[str, Any]:
    """Heurística absoluta no raio (Fase 1). Baixa amostra → baixa confiança."""
    _, min_ok, conf_alta, conf_baixa = _params_completude()
    n = max(0, int(n_features or 0))
    if n >= min_ok:
        return {
            "completude": "alta",
            "confianca": conf_alta,
            "n_features": n,
            "limiar_min": min_ok,
            "nota_completude": None,
        }
    return {
        "completude": "baixa",
        "confianca": conf_baixa if n > 0 else 0,
        "n_features": n,
        "limiar_min": min_ok,
        "nota_completude": (
            "Dados do OSM nesta área são esparsos; verificação em campo e junto "
            "à prefeitura é fortemente recomendada."
        ),
    }


def _contar_tags(elements: list[dict]) -> tuple[dict[str, int], dict[str, int]]:
    landuse: dict[str, int] = {}
    zoning: dict[str, int] = {}
    for el in elements:
        tags = el.get("tags") or {}
        lu = (tags.get("landuse") or "").strip().lower()
        if lu:
            landuse[lu] = landuse.get(lu, 0) + 1
        zo = (tags.get("zoning") or "").strip().lower()
        if zo:
            zoning[zo] = zoning.get(zo, 0) + 1
    return landuse, zoning


def consultar_osm_proxy(
    latitude: float, longitude: float, *, raio_m: int | None = None,
) -> dict[str, Any] | None:
    """Overpass landuse+zoning no raio. Retorna perfil empírico ou None."""
    raio_cfg, _, _, _ = _params_completude()
    raio = raio_cfg if raio_m is None else max(50, min(int(raio_m), 500))
    query = f"""
    [out:json][timeout:15];
    (
      way(around:{raio},{latitude},{longitude})["landuse"];
      relation(around:{raio},{latitude},{longitude})["landuse"];
      node(around:{raio},{latitude},{longitude})["landuse"];
      way(around:{raio},{latitude},{longitude})["zoning"];
      relation(around:{raio},{latitude},{longitude})["zoning"];
    );
    out tags center 40;
    """
    try:
        with httpx.Client(
            timeout=20,
            headers={"User-Agent": "GymSite-ZEUS/1.0 (osm-proxy-fase1)"},
        ) as c:
            r = c.post("https://overpass-api.de/api/interpreter", data={"data": query})
        if r.status_code != 200:
            logger.warning("zeus OSM HTTP %s", r.status_code)
            return None
        elements = (r.json() or {}).get("elements") or []
        landuse, zoning = _contar_tags(elements)
        if not landuse and not zoning:
            return None
        # Prefer landuse; zoning só se não houver landuse.
        if landuse:
            tag = max(landuse.items(), key=lambda kv: kv[1])[0]
            origem_tag = "landuse"
        else:
            tag = max(zoning.items(), key=lambda kv: kv[1])[0]
            origem_tag = "zoning"
        n = sum(landuse.values()) + sum(zoning.values())
        comp = avaliar_completude(n)
        return {
            "tag_osm": tag,
            "origem_tag": origem_tag,
            "uso_observado": rotular_uso_observado(tag),
            "landuse_counts": landuse,
            "zoning_counts": zoning,
            "raio_m": raio,
            **comp,
        }
    except Exception as e:
        logger.warning("zeus OSM falha: %s", e)
        return None


# Top-20 municípios por população (IBGE ~2024) — âncoras p/ validação Fase 1.
TOP20_MUNICIPIOS_VALIDACAO: list[dict[str, Any]] = [
    {"cidade": "São Paulo", "uf": "SP", "lat": -23.5505, "lon": -46.6333, "pop_ordem": 1},
    {"cidade": "Rio de Janeiro", "uf": "RJ", "lat": -22.9068, "lon": -43.1729, "pop_ordem": 2},
    {"cidade": "Brasília", "uf": "DF", "lat": -15.7939, "lon": -47.8828, "pop_ordem": 3},
    {"cidade": "Fortaleza", "uf": "CE", "lat": -3.7319, "lon": -38.5267, "pop_ordem": 4,
     "tem_ckan": True},
    {"cidade": "Salvador", "uf": "BA", "lat": -12.9714, "lon": -38.5014, "pop_ordem": 5},
    {"cidade": "Belo Horizonte", "uf": "MG", "lat": -19.9167, "lon": -43.9345, "pop_ordem": 6,
     "tem_geojson_utm": True},
    {"cidade": "Manaus", "uf": "AM", "lat": -3.1190, "lon": -60.0217, "pop_ordem": 7},
    {"cidade": "Curitiba", "uf": "PR", "lat": -25.4284, "lon": -49.2733, "pop_ordem": 8},
    {"cidade": "Recife", "uf": "PE", "lat": -8.0476, "lon": -34.8770, "pop_ordem": 9,
     "tem_geojson_wgs84": True},
    {"cidade": "Goiânia", "uf": "GO", "lat": -16.6869, "lon": -49.2648, "pop_ordem": 10},
    {"cidade": "Belém", "uf": "PA", "lat": -1.4558, "lon": -48.4902, "pop_ordem": 11},
    {"cidade": "Porto Alegre", "uf": "RS", "lat": -30.0346, "lon": -51.2177, "pop_ordem": 12,
     "tem_shapefile": True},
    {"cidade": "Guarulhos", "uf": "SP", "lat": -23.4538, "lon": -46.5333, "pop_ordem": 13},
    {"cidade": "Campinas", "uf": "SP", "lat": -22.9056, "lon": -47.0608, "pop_ordem": 14},
    {"cidade": "São Gonçalo", "uf": "RJ", "lat": -22.8268, "lon": -43.0634, "pop_ordem": 15},
    {"cidade": "São Luís", "uf": "MA", "lat": -2.5307, "lon": -44.3068, "pop_ordem": 16},
    {"cidade": "Maceió", "uf": "AL", "lat": -9.6658, "lon": -35.7350, "pop_ordem": 17},
    {"cidade": "Duque de Caxias", "uf": "RJ", "lat": -22.7858, "lon": -43.3059, "pop_ordem": 18},
    {"cidade": "Natal", "uf": "RN", "lat": -5.7793, "lon": -35.2009, "pop_ordem": 19},
    {"cidade": "Teresina", "uf": "PI", "lat": -5.0892, "lon": -42.8019, "pop_ordem": 20},
]


def invariantes_proxy(perfil: dict[str, Any]) -> list[str]:
    """Falhas de contrato Fase 1 (anti-alucinação)."""
    errs: list[str] = []
    if perfil.get("compatibilidade") not in (None, "INDIVIDUALIZAR"):
        errs.append("proxy não pode emitir veredito legal")
    uso = (perfil.get("uso_observado") or perfil.get("uso_predominante_osm") or "")
    if uso and uso.upper() in ("PERMISSIVO", "CONDICIONADO", "RESTRITO"):
        errs.append("rótulo OSM não pode ser veredito LUOS")
    return errs
