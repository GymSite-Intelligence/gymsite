"""
Payload do mapa municipal (viewer) — concorrentes + entrantes CNPJ 90d.
Geocodifica município e entrantes sem lat (cap de chamadas).
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from tools.maps_tools import geocode_endereco

_SEGMENTOS_MAPA = frozenset(
    {"academia", "crossfit_box", "studio_funcional", "studio_pilates"}
)
_MAX_GEOCODE_ENTRANTES = 25
_MAX_GEOCODE_CONCORRENTES = 25


def _num_coord(v: Any) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
        if f == 0.0:
            return None
        return f
    except (TypeError, ValueError):
        return None


def _viewport_to_bounds(viewport: dict | None) -> dict[str, dict[str, float]] | None:
    if not isinstance(viewport, dict):
        return None
    ne = viewport.get("ne") if isinstance(viewport.get("ne"), dict) else None
    sw = viewport.get("sw") if isinstance(viewport.get("sw"), dict) else None
    if not ne or not sw:
        return None
    nelat = _num_coord(ne.get("lat"))
    nelng = _num_coord(ne.get("lng"))
    swlat = _num_coord(sw.get("lat"))
    swlng = _num_coord(sw.get("lng"))
    if None in (nelat, nelng, swlat, swlng):
        return None
    assert nelat is not None and nelng is not None and swlat is not None and swlng is not None
    return {
        "ne": {"lat": nelat, "lng": nelng},
        "sw": {"lat": swlat, "lng": swlng},
    }


def _bounds_from_coords(coords: list[tuple[float, float]], *, pad_deg: float = 0.02) -> dict | None:
    if not coords:
        return None
    lats = [c[0] for c in coords]
    lngs = [c[1] for c in coords]
    return {
        "ne": {"lat": max(lats) + pad_deg, "lng": max(lngs) + pad_deg},
        "sw": {"lat": min(lats) - pad_deg, "lng": min(lngs) - pad_deg},
    }


def _geocode_cidade(cidade: str, uf: str) -> dict[str, Any]:
    parts = [p.strip() for p in (cidade, uf, "Brasil") if p and str(p).strip()]
    endereco = ", ".join(parts)
    geo = geocode_endereco(endereco)
    if geo.get("error"):
        return {"error": geo.get("error"), "endereco": endereco}
    lat = _num_coord(geo.get("lat"))
    lng = _num_coord(geo.get("lng"))
    if lat is None or lng is None:
        return {"error": "coordenadas_invalidas", "endereco": endereco}
    bounds = _viewport_to_bounds(geo.get("viewport"))
    if bounds is None and lat is not None and lng is not None:
        bounds = _bounds_from_coords([(lat, lng)], pad_deg=0.08)
    out: dict[str, Any] = {
        "centro": {"lat": lat, "lng": lng},
        "endereco": endereco,
        "fonte": geo.get("fonte_geocode") or geo.get("fonte") or "geocode",
    }
    if bounds:
        out["bounds"] = bounds
    return out


def _entrante_endereco(ent: dict, cidade: str, uf: str) -> str | None:
    parts = []
    for key in ("endereco", "logradouro"):
        v = (ent.get(key) or "").strip()
        if v:
            parts.append(v)
            break
    num = (ent.get("numero") or "").strip()
    if num and parts:
        parts[0] = f"{parts[0]}, {num}"
    bairro = (ent.get("bairro") or "").strip()
    if bairro:
        parts.append(bairro)
    if cidade:
        parts.append(cidade)
    if uf:
        parts.append(uf[:2].upper())
    parts.append("Brasil")
    joined = ", ".join(p for p in parts if p)
    return joined if len(joined) > 12 else None


def _peso_recencia_entrante(data_abertura: str | None, dias_janela: int = 90) -> float:
    if not data_abertura:
        return 1.0
    try:
        abertura = date.fromisoformat(str(data_abertura)[:10])
    except ValueError:
        return 1.0
    dias = max(0, (date.today() - abertura).days)
    # Mais recente → peso maior (1.0 no dia 0, ~0.35 no fim da janela)
    return max(0.35, 1.0 - (dias / max(dias_janela, 1)) * 0.65)


def _filtrar_entrantes_mapa(entrantes: list[dict]) -> list[dict]:
    out: list[dict] = []
    for ent in entrantes:
        if not isinstance(ent, dict):
            continue
        if ent.get("incluir_no_parque") is False:
            continue
        seg = (ent.get("segmento_operacao") or "").strip().lower()
        if seg and seg not in _SEGMENTOS_MAPA:
            continue
        out.append(ent)
    return out


def _geocode_entrantes(
    entrantes: list[dict],
    cidade: str,
    uf: str,
    *,
    max_calls: int = _MAX_GEOCODE_ENTRANTES,
) -> list[dict]:
    geocoded = 0
    rows: list[dict] = []
    for ent in entrantes:
        lat = _num_coord(ent.get("lat"))
        lng = _num_coord(ent.get("lng"))
        if lat is None or lng is None:
            if geocoded < max_calls:
                addr = _entrante_endereco(ent, cidade, uf)
                if addr:
                    geo = geocode_endereco(addr)
                    if "error" not in geo:
                        lat = _num_coord(geo.get("lat"))
                        lng = _num_coord(geo.get("lng"))
                        geocoded += 1
        if lat is None or lng is None:
            continue
        rows.append(
            {
                "cnpj": ent.get("cnpj"),
                "nome_exibicao": ent.get("nome_exibicao") or ent.get("nome_fantasia"),
                "bairro": ent.get("bairro"),
                "data_abertura": ent.get("data_abertura"),
                "segmento_operacao": ent.get("segmento_operacao"),
                "lat": lat,
                "lng": lng,
                "peso_heatmap": round(_peso_recencia_entrante(ent.get("data_abertura")), 3),
            }
        )
    return rows


def _geocode_competidores(
    competidores: list[dict],
    *,
    max_calls: int = _MAX_GEOCODE_CONCORRENTES,
) -> tuple[list[dict], int]:
    """Preenche lat/lng via endereco quando a linha no DB veio sem geo (relatórios antigos)."""
    geocoded = 0
    rows: list[dict] = []
    for c in competidores:
        if not isinstance(c, dict):
            continue
        row = dict(c)
        lat = _num_coord(row.get("lat"))
        lng = _num_coord(row.get("lng"))
        if (lat is None or lng is None) and geocoded < max_calls:
            addr = (row.get("endereco") or "").strip()
            if addr:
                geo = geocode_endereco(addr)
                if "error" not in geo:
                    glat = _num_coord(geo.get("lat"))
                    glng = _num_coord(geo.get("lng"))
                    if glat is not None and glng is not None:
                        row["lat"] = glat
                        row["lng"] = glng
                        geocoded += 1
        rows.append(row)
    return rows, geocoded


def _competidor_mapa_row(c: dict) -> dict | None:
    lat = _num_coord(c.get("lat"))
    lng = _num_coord(c.get("lng"))
    if lat is None or lng is None:
        return None
    rating = c.get("rating_oficial") or c.get("rating_geral")
    try:
        rating_f = float(rating) if rating is not None else None
    except (TypeError, ValueError):
        rating_f = None
    return {
        "nome": c.get("nome"),
        "place_id": c.get("place_id"),
        "lat": lat,
        "lng": lng,
        "distancia_km": c.get("distancia_km"),
        "rating": rating_f,
        "bairro_concorrente": c.get("bairro_concorrente"),
        "google_maps_uri": c.get("google_maps_uri"),
    }


def build_mapa_mercado_payload(
    *,
    cidade: str,
    uf: str,
    bairro: str,
    competidores: list[dict],
    entrantes_block: dict | None,
    site_lat: float | None = None,
    site_lng: float | None = None,
) -> dict[str, Any]:
    """Monta JSON para GET /api/relatorios/{id}/mapa-mercado."""
    cidade = (cidade or "").strip()
    uf = (uf or "").strip()[:2].upper()
    bairro = (bairro or "").strip()

    municipio = _geocode_cidade(cidade, uf)
    site = None
    if site_lat is not None and site_lng is not None:
        site = {"lat": site_lat, "lng": site_lng, "label": bairro or cidade}
    elif bairro and cidade:
        geo_site = geocode_endereco(
            ", ".join(p for p in (bairro, cidade, uf, "Brasil") if p)
        )
        if "error" not in geo_site:
            slat = _num_coord(geo_site.get("lat"))
            slng = _num_coord(geo_site.get("lng"))
            if slat is not None and slng is not None:
                site = {"lat": slat, "lng": slng, "label": bairro}

    comps_enriched, concorrentes_geocoded = _geocode_competidores(competidores)
    concorrentes = [
        row
        for c in comps_enriched
        for row in [_competidor_mapa_row(c)]
        if row
    ]

    block = entrantes_block if isinstance(entrantes_block, dict) else {}
    entrantes_raw = [
        e for e in (block.get("entrantes") or []) if isinstance(e, dict)
    ]
    entrantes_filtrados = _filtrar_entrantes_mapa(entrantes_raw)
    entrantes = _geocode_entrantes(
        entrantes_filtrados,
        block.get("cidade") or cidade,
        block.get("uf") or uf,
    )

    bounds_municipio = municipio.get("bounds")
    if bounds_municipio is None:
        pin_coords: list[tuple[float, float]] = []
        centro = (municipio.get("centro") or {}) if isinstance(municipio, dict) else {}
        clat = _num_coord(centro.get("lat"))
        clng = _num_coord(centro.get("lng"))
        if clat is not None and clng is not None:
            pin_coords.append((clat, clng))
        for row in concorrentes + entrantes:
            plat = _num_coord(row.get("lat"))
            plng = _num_coord(row.get("lng"))
            if plat is not None and plng is not None:
                pin_coords.append((plat, plng))
        if site and site.get("lat") is not None and site.get("lng") is not None:
            pin_coords.append((float(site["lat"]), float(site["lng"])))
        bounds_municipio = _bounds_from_coords(pin_coords)

    return {
        "cidade": cidade,
        "uf": uf,
        "bairro_estudo": bairro,
        "municipio": municipio,
        "bounds_municipio": bounds_municipio,
        "site": site,
        "concorrentes": concorrentes,
        "concorrentes_total_db": len(
            [c for c in competidores if isinstance(c, dict)]
        ),
        "concorrentes_geocoded_runtime": concorrentes_geocoded,
        "concorrentes_com_coord": len(concorrentes),
        "entrantes": entrantes,
        "entrantes_total_filtrado": len(entrantes_filtrados),
        "entrantes_com_coord": len(entrantes),
        "gerado_em": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
