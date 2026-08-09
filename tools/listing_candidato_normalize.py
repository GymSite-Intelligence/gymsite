from __future__ import annotations

import math
import re
import unicodedata


def _norm(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").lower())
    return re.sub(r"\s+", " ", text.encode("ascii", "ignore").decode()).strip()


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_m = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * radius_m * math.asin(math.sqrt(a))


def _geografia_compativel(row: dict, cidade: str, uf: str) -> bool:
    blob = _norm(
        " ".join(
            str(row.get(key) or "")
            for key in ("endereco", "titulo", "snippet")
        )
    )
    target_city = _norm(cidade)
    target_uf = _norm(uf).upper()
    explicit_ufs = {
        match.upper()
        for match in re.findall(r"(?:-|/)\s*([A-Z]{2})(?:\b|$)", str(
            " ".join(str(row.get(key) or "") for key in ("endereco", "titulo"))
        ), re.IGNORECASE)
    }
    if explicit_ufs and target_uf not in explicit_ufs:
        return False
    if target_city and explicit_ufs and target_city not in blob:
        return False
    return True


def normalizar_listings(
    rows: list[dict],
    *,
    cidade: str,
    uf: str,
    bairro: str,
    lat0: float | None,
    lng0: float | None,
) -> list[dict]:
    out: list[dict] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        try:
            area_m2 = float(row.get("area_m2") or 0)
        except (TypeError, ValueError):
            continue
        if area_m2 <= 0 or not _geografia_compativel(row, cidade, uf):
            continue

        lat = row.get("latitude")
        lng = row.get("longitude")
        try:
            lat_value = float(lat) if lat is not None else None
            lng_value = float(lng) if lng is not None else None
        except (TypeError, ValueError):
            lat_value = lng_value = None

        endereco = str(row.get("endereco") or "").strip()
        if not endereco and (lat_value is None or lng_value is None):
            continue

        geocoded = lat_value is not None and lng_value is not None
        if geocoded and lat0 is not None and lng0 is not None:
            distance_m = _haversine_m(lat_value, lng_value, lat0, lng0)
            score = round(max(0.0, min(10.0, 10.0 * (1.0 - distance_m / 2500.0))), 2)
        else:
            distance_m = None
            score = 0.0

        price = row.get("preco")
        candidate = {
            "place_id": f"listing_cascata_{index}",
            "nome": row.get("titulo") or f"Imóvel anunciado · {area_m2:g} m²",
            "endereco": endereco or f"{bairro}, {cidade} - {uf}",
            "cidade": cidade,
            "uf": uf,
            "bairro": bairro,
            "lat": lat_value,
            "lng": lng_value,
            "tipos": ["imovel_anunciado", "comercial"],
            "area_m2": area_m2,
            "area_estimada_m2": area_m2,
            "score_geoscout": score,
            "distancia_centroide_m": round(distance_m, 1) if distance_m is not None else None,
            "qualidade_sinal": "direto-listing-bairro",
            "fonte": row.get("fonte") or "listing_cascata",
            "source": "listing_cascata",
            "listing_url": row.get("url"),
            "price_raw": f"R$ {price:.0f}" if isinstance(price, (int, float)) else None,
            "modalidade": "locacao",
            "geocoded": geocoded,
            "score_ancoragem": 0.0,
            "polos_geradores": [],
            "motivo": f"Imóvel anunciado em {bairro}; validar anúncio antes da visita.",
        }
        out.append(candidate)
    return out
