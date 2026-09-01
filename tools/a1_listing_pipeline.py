from __future__ import annotations

import logging

from tools.listing_candidato_normalize import normalizar_listings

_PALAVRAS_RESIDENCIAL = [
    "apartamento",
    "apart",
    "quartos à venda",
    "quarto à venda",
    "casa à venda",
    "casas à venda",
    "residencial",
    "cobertura",
    "studio residencial",
    "kitnet",
    "loft residencial",
]

_PALAVRAS_VENDA = ["à venda", "a venda", "venda", "comprar", "compra"]

_logger_a1 = logging.getLogger("gymsite.a1")


def filtrar_candidatos_comerciais(
    candidatos: list[dict],
    area_m2_min: int | None,
    area_m2_max: int | None,
) -> tuple[list[dict], dict]:
    """Remove venda, residencial e área fora da faixa. Fail-soft: mantém lista se entrada vazia."""
    if not candidatos:
        return [], {"total": 0, "venda": 0, "residencial": 0, "area": 0}

    filtrados: list[dict] = []
    removidos = {"venda": 0, "residencial": 0, "area": 0}

    for c in candidatos:
        if not isinstance(c, dict):
            continue

        nome = str(c.get("nome") or "").lower()
        modalidade = str(c.get("modalidade") or "").lower()
        area = c.get("area_m2")

        if modalidade == "venda" or any(p in nome for p in _PALAVRAS_VENDA):
            removidos["venda"] += 1
            continue

        if any(p in nome for p in _PALAVRAS_RESIDENCIAL):
            removidos["residencial"] += 1
            continue

        if area is not None:
            try:
                area_num = float(area)
                if area_m2_min is not None and area_num < float(area_m2_min):
                    removidos["area"] += 1
                    continue
                if area_m2_max is not None and area_num > float(area_m2_max):
                    removidos["area"] += 1
                    continue
            except (TypeError, ValueError):
                pass

        filtrados.append(c)

    removidos["total"] = len(candidatos) - len(filtrados)
    _logger_a1.info(
        "A1 filtro comercial: %d mantidos, %d removidos "
        "(venda=%d, residencial=%d, area=%d) · area %s-%s m²",
        len(filtrados),
        removidos["total"],
        removidos["venda"],
        removidos["residencial"],
        removidos["area"],
        area_m2_min,
        area_m2_max,
    )
    return filtrados, removidos


def _fmt_brl(value: float) -> str:
    return f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _as_positive_int(value: object, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _anexar_mrlr(candidatos: list[dict], cidade: str, bairro: str) -> list[dict]:
    from tools.aluguel_mrlr import aluguel_deterministico

    cache: dict[int, dict] = {}
    for candidate in candidatos:
        area = _as_positive_int(
            candidate.get("area_m2") or candidate.get("area_estimada_m2"),
            0,
        )
        if not area:
            continue
        if area not in cache:
            try:
                cache[area] = aluguel_deterministico(
                    area_m2=area,
                    cidade=cidade,
                    bairro=bairro,
                )
            except Exception as exc:
                cache[area] = {"status": "indisponivel", "motivo": str(exc)}
        result = cache[area]
        if result.get("status") != "ok":
            candidate["aluguel_mrlr_status"] = result.get("status") or "indisponivel"
            candidate["aluguel_mrlr_motivo"] = result.get("motivo")
            continue
        total = result.get("aluguel_total")
        unit = result.get("valor_unitario_m2")
        source = result.get("fonte") or "MRLR"
        candidate["aluguel_estimado"] = total
        candidate["aluguel_unitario_m2"] = unit
        candidate["aluguel_fonte"] = source
        candidate["aluguel_carimbo"] = (
            f"R$ {_fmt_brl(float(total))} · {area} m² do listing"
            f" · {source} · R$ {_fmt_brl(float(unit))}/m²"
        )
    return candidatos


def buscar_candidatos_listing_mrlr(
    *,
    cidade: str,
    uf: str,
    bairro: str,
    area_m2_min: int = 500,
    area_m2_max: int = 5000,
) -> dict:
    from tools.listing_cascata import buscar_candidatos_cascata

    area_min = _as_positive_int(area_m2_min, 500)
    area_max = _as_positive_int(area_m2_max, 5000)
    if area_max < area_min:
        area_min, area_max = area_max, area_min

    rows = buscar_candidatos_cascata(
        cidade,
        bairro,
        uf,
        area_min,
        area_max,
    )
    first = rows[0] if rows and isinstance(rows[0], dict) else {}
    lat0 = first.get("bairro_centro_lat")
    lng0 = first.get("bairro_centro_lng")
    candidates = normalizar_listings(
        rows,
        cidade=cidade,
        uf=uf,
        bairro=bairro,
        lat0=lat0,
        lng0=lng0,
    )
    candidates, stats_removidos = filtrar_candidatos_comerciais(
        candidates,
        area_m2_min=area_min,
        area_m2_max=area_max,
    )
    if not candidates:
        return {
            "status": "ok_vazio",
            "total_candidatos": 0,
            "candidatos": [],
            "fonte": "listing_cascata_searchapi+mrlr",
            "cidade": cidade,
            "uf": uf,
            "bairro": bairro,
            "area_m2_min": area_min,
            "area_m2_max": area_max,
            "aviso": (
                "Nenhum imóvel comercial para aluguel encontrado na faixa de área. "
                "O referencial de viabilidade é do bairro/vias (não de imóvel específico). "
                f"Filtro aplicado: {stats_removidos['total']} removidos."
            ),
            "stats_removidos": stats_removidos,
            "modo_prospeccao": "vias_por_fluxo",
            "carimbo": f"filtro comercial aplicado · area {area_min}-{area_max} m²",
        }

    candidates = _anexar_mrlr(candidates, cidade, bairro)
    return {
        "status": "ok",
        "total_candidatos": len(candidates),
        "candidatos": candidates,
        "fonte": "listing_cascata_searchapi+mrlr",
        "cidade": cidade,
        "uf": uf,
        "bairro": bairro,
        "area_m2_min": area_min,
        "area_m2_max": area_max,
        "aviso": None,
        "stats_removidos": stats_removidos,
        "modo_prospeccao": "candidatos",
        "carimbo": f"MRLR + filtro comercial · area {area_min}-{area_max} m²",
    }
