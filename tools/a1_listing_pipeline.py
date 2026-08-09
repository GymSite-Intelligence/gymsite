from __future__ import annotations

from tools.listing_candidato_normalize import normalizar_listings


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
    candidates = _anexar_mrlr(candidates, cidade, bairro)
    status = "ok" if candidates else "ok_vazio"
    warning = None
    if not candidates:
        warning = (
            "Nenhum anúncio individual com área e localização verificáveis foi "
            "encontrado no bairro. Não foram usados pontos comerciais heurísticos."
        )
    return {
        "status": status,
        "total_candidatos": len(candidates),
        "candidatos": candidates,
        "fonte": "listing_cascata_searchapi+mrlr",
        "cidade": cidade,
        "uf": uf,
        "bairro": bairro,
        "area_m2_min": area_min,
        "area_m2_max": area_max,
        "aviso": warning,
    }
