from __future__ import annotations


def score_payback_norm(payback_meses: float | None) -> float:
    if payback_meses is None:
        return 0.0
    try:
        value = float(payback_meses)
    except (TypeError, ValueError):
        return 0.0
    if value <= 12:
        return 1.0
    if value >= 48:
        return 0.0
    return round((48.0 - value) / 36.0, 4)


def _mid_scenario(analysis: dict) -> dict | None:
    scenarios = analysis.get("cenarios") if isinstance(analysis, dict) else None
    if not isinstance(scenarios, dict):
        return None
    for key in ("mid", "medio", "médio"):
        value = scenarios.get(key)
        if isinstance(value, dict):
            return value
    for value in scenarios.values():
        if isinstance(value, dict) and str(value.get("modelo_key") or "").lower() == "mid":
            return value
    return None


def _as_positive_float(value: object) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _fmt_brl(value: float) -> str:
    return f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _enrich(candidate: dict, scenario: dict | None) -> dict:
    item = dict(candidate)
    geo = max(0.0, min(10.0, float(candidate.get("score_geoscout") or 0)))
    item["score_geo_norm"] = round(geo / 10.0, 4)
    item["payback_est_meses"] = None
    item["score_payback_norm"] = 0.0
    item["score_composto"] = round(0.35 * item["score_geo_norm"], 4)

    rent = _as_positive_float(candidate.get("aluguel_estimado"))
    area = _as_positive_float(
        candidate.get("area_m2") or candidate.get("area_estimada_m2")
    )
    unit = _as_positive_float(candidate.get("aluguel_unitario_m2"))
    source = str(candidate.get("aluguel_fonte") or "")
    is_mrlr = rent is not None and "mrlr" in source.lower()
    if is_mrlr:
        item["aluguel_mrlr_mensal"] = rent
        item["aluguel_fonte"] = source
        item["carimbo_aluguel"] = candidate.get("aluguel_carimbo") or (
            f"R$ {_fmt_brl(rent)} · {area:g} m² do listing"
            f" · {source} · R$ {_fmt_brl(unit)}/m²"
            if area is not None and unit is not None
            else f"R$ {_fmt_brl(rent)} · área do listing · {source} · coleta atual"
        )
    else:
        item["aluguel_mrlr_mensal"] = None
        item["carimbo_aluguel"] = None

    if not scenario:
        item["aviso_viabilidade"] = (
            "Viabilidade indisponível — ordenação apenas por localização."
        )
        return item
    if not is_mrlr:
        item["aviso_viabilidade"] = (
            "MRLR indisponível para este imóvel — payback não calculado."
        )
        return item

    investment = _as_positive_float(scenario.get("investimento_total"))
    old_profit = _as_positive_float(scenario.get("lucro_mensal_estimado"))
    costs = (
        scenario.get("custos_detalhados")
        if isinstance(scenario.get("custos_detalhados"), dict)
        else {}
    )
    old_rent = _as_positive_float(costs.get("aluguel"))
    old_condo = _as_positive_float(costs.get("condominio")) or 0.0
    if not all((investment, old_profit, old_rent)):
        item["aviso_viabilidade"] = (
            "Snapshot A4 mid incompleto — payback não calculado."
        )
        return item

    condo_rate = old_condo / old_rent
    new_profit = old_profit + old_rent + old_condo - rent - (rent * condo_rate)
    payback = investment / new_profit if new_profit > 0 else 999.0
    item["payback_est_meses"] = round(payback, 1)
    item["score_payback_norm"] = score_payback_norm(payback)
    item["score_composto"] = round(
        0.35 * item["score_geo_norm"] + 0.65 * item["score_payback_norm"],
        4,
    )
    item["aviso_viabilidade"] = None
    return item


def rank_candidatos_viabilidade(
    candidatos: list[dict],
    analise_financeira: dict,
) -> list[dict]:
    scenario = _mid_scenario(analise_financeira)
    enriched = [
        _enrich(candidate, scenario)
        for candidate in candidatos
        if isinstance(candidate, dict)
    ]
    return sorted(
        enriched,
        key=lambda item: (
            float(item.get("score_composto") or 0),
            float(item.get("score_geoscout") or 0),
            str(item.get("endereco") or ""),
        ),
        reverse=True,
    )
