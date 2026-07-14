"""
Comparativo CUB estadual × SINAPI (SIDRA 2296) — golden states.

Uso: avaliar oscilação entre índices; produção usa CUB via `tools/obra_regua.py` (OBRA_REGUA=cub).
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

from tools.sinapi_indices import FATOR_OBRA_ADAPTACAO, obra_adaptacao_por_modelo

ROOT = Path(__file__).resolve().parent.parent
CUB_GOLDEN_PATH = ROOT / "data" / "cub_pilot" / "cub_estadual_golden.json"
SINAPI_GOLDEN_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "cub_sinapi" / "sinapi_snapshot_golden.json"
)
EXPECTATIONS_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "cub_sinapi" / "golden_states.json"
)


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON inválido: {path}")
    return data


def load_cub_golden(path: Path | None = None) -> dict[str, Any]:
    return _load_json(path or CUB_GOLDEN_PATH)


def load_sinapi_golden(path: Path | None = None) -> dict[str, Any]:
    return _load_json(path or SINAPI_GOLDEN_PATH)


def load_expectations(path: Path | None = None) -> dict[str, Any]:
    return _load_json(path or EXPECTATIONS_PATH)


def compare_uf(
    uf: str,
    *,
    cub_data: dict[str, Any] | None = None,
    sinapi_data: dict[str, Any] | None = None,
    fator_obra: float = FATOR_OBRA_ADAPTACAO,
) -> dict[str, Any] | None:
    """Compara uma UF. Retorna None se faltar CUB ou SINAPI."""
    uf = (uf or "").strip().upper()
    cub_data = cub_data or load_cub_golden()
    sinapi_data = sinapi_data or load_sinapi_golden()

    cub_block = (cub_data.get("por_uf") or {}).get(uf) or {}
    sin_block = (sinapi_data.get("por_uf") or {}).get(uf) or {}
    cub_m2 = cub_block.get("cub_m2")
    sinapi_m2 = sin_block.get("sinapi_custo_m2")
    if cub_m2 is None or sinapi_m2 is None:
        return None

    cub_m2 = float(cub_m2)
    sinapi_m2 = float(sinapi_m2)
    ratio = cub_m2 / sinapi_m2
    delta_pct = (cub_m2 - sinapi_m2) / sinapi_m2 * 100.0
    obra_mid = obra_adaptacao_por_modelo(sinapi_m2)["mid"]
    obra_pct_cub = obra_mid / cub_m2 * 100.0
    fator_implicito_cub = obra_mid / cub_m2

    return {
        "uf": uf,
        "cub_m2": round(cub_m2, 2),
        "sinapi_m2": round(sinapi_m2, 2),
        "cub_periodo": cub_block.get("periodo_ref"),
        "sinapi_periodo": sin_block.get("periodo_ref") or sinapi_data.get("periodo_ref"),
        "cub_fonte_uf": cub_block.get("fonte_uf"),
        "ratio_cub_sinapi": round(ratio, 4),
        "delta_pct": round(delta_pct, 2),
        "obra_adaptacao_mid": obra_mid,
        "obra_pct_cub": round(obra_pct_cub, 1),
        "fator_implicito_cub": round(fator_implicito_cub, 4),
        "obra_cub_fator_atual": round(cub_m2 * fator_obra, 2),
        "delta_obra_sinapi_vs_cub_pct": round(
            (obra_mid - cub_m2 * fator_obra) / obra_mid * 100.0, 2
        ),
        "carimbo_cub": f"{cub_m2:.2f} R$/m² · CUB estadual · {cub_block.get('fonte_uf', 'SindusCon')} · {cub_block.get('periodo_ref', 'n/d')}",
        "carimbo_sinapi": (
            f"{sinapi_m2:.2f} R$/m² · IBGE SIDRA SINAPI 2296 · Caixa/IBGE · "
            f"{sin_block.get('periodo_ref') or sinapi_data.get('periodo_ref', 'n/d')}"
        ),
    }


def compare_all(
    ufs: list[str] | None = None,
    *,
    cub_data: dict[str, Any] | None = None,
    sinapi_data: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    cub_data = cub_data or load_cub_golden()
    sinapi_data = sinapi_data or load_sinapi_golden()
    if ufs is None:
        cub_ufs = set((cub_data.get("por_uf") or {}).keys())
        sin_ufs = set((sinapi_data.get("por_uf") or {}).keys())
        ufs = sorted(cub_ufs & sin_ufs)
    rows = []
    for uf in ufs:
        row = compare_uf(uf, cub_data=cub_data, sinapi_data=sinapi_data)
        if row:
            rows.append(row)
    return rows


def aggregate_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    ratios = [r["ratio_cub_sinapi"] for r in rows]
    deltas = [r["delta_pct"] for r in rows]
    obra_pcts = [r["obra_pct_cub"] for r in rows]
    fatores = [r["fator_implicito_cub"] for r in rows]
    return {
        "n_ufs": len(rows),
        "ratio_cub_sinapi_mean": round(statistics.mean(ratios), 4),
        "ratio_cub_sinapi_stdev": round(statistics.pstdev(ratios), 4),
        "ratio_cub_sinapi_min": round(min(ratios), 4),
        "ratio_cub_sinapi_max": round(max(ratios), 4),
        "delta_pct_mean": round(statistics.mean(deltas), 2),
        "obra_pct_cub_mean": round(statistics.mean(obra_pcts), 1),
        "fator_implicito_cub_mean": round(statistics.mean(fatores), 4),
    }


def rank_ufs(rows: list[dict[str, Any]], key: str, top_n: int = 5) -> list[str]:
    ordered = sorted(rows, key=lambda r: r[key], reverse=True)
    return [r["uf"] for r in ordered[:top_n]]


def rank_overlap(rows: list[dict[str, Any]], top_n: int = 5) -> dict[str, Any]:
    top_cub = set(rank_ufs(rows, "cub_m2", top_n))
    top_sin = set(rank_ufs(rows, "sinapi_m2", top_n))
    return {
        "top_cub": sorted(top_cub, key=lambda u: next(r["cub_m2"] for r in rows if r["uf"] == u), reverse=True),
        "top_sinapi": sorted(top_sin, key=lambda u: next(r["sinapi_m2"] for r in rows if r["uf"] == u), reverse=True),
        "overlap": len(top_cub & top_sin),
        "overlap_ufs": sorted(top_cub & top_sin),
        "only_cub": sorted(top_cub - top_sin),
        "only_sinapi": sorted(top_sin - top_cub),
    }


def validate_against_golden(
    rows: list[dict[str, Any]],
    expectations: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Valida linhas computadas vs golden_states.json. Retorna falhas."""
    expectations = expectations or load_expectations()
    tol = expectations.get("tolerancias") or {}
    failures: list[str] = []
    por_uf = expectations.get("por_uf") or {}

    row_ufs = {r["uf"] for r in rows}
    for uf, exp in por_uf.items():
        if uf not in row_ufs:
            continue
        row = next((r for r in rows if r["uf"] == uf), None)
        if not row:
            failures.append(f"{uf}: sem linha comparativa")
            continue
        for field, abs_tol in (
            ("ratio_cub_sinapi", tol.get("ratio_cub_sinapi_abs", 0.015)),
            ("delta_pct", tol.get("delta_pct_abs", 1.5)),
            ("obra_pct_cub", tol.get("obra_pct_cub_abs", 0.6)),
            ("fator_implicito_cub", tol.get("fator_implicito_cub_abs", 0.006)),
        ):
            got = row[field]
            want = exp[field]
            if abs(got - want) > abs_tol:
                failures.append(f"{uf}.{field}: got {got} want {want} ±{abs_tol}")

    agg = aggregate_metrics(rows)
    agg_exp = expectations.get("agregados_nacionais_27uf") or {}
    full_national = len(rows) >= 25
    if full_national:
        for field, abs_tol in (
            ("ratio_cub_sinapi_mean", tol.get("ratio_mean_abs", 0.02)),
            ("ratio_cub_sinapi_stdev", tol.get("ratio_stdev_abs", 0.005)),
        ):
            got = agg.get(field)
            want = agg_exp.get(field)
            if got is not None and want is not None and abs(got - want) > abs_tol:
                failures.append(f"agg.{field}: got {got} want {want} ±{abs_tol}")

        rank = rank_overlap(rows, top_n=5)
        min_overlap = int(tol.get("rank_top5_overlap_min", 4))
        if rank["overlap"] < min_overlap:
            failures.append(
                f"rank_top5 overlap {rank['overlap']} < {min_overlap} "
                f"(cub={rank['top_cub']} sinapi={rank['top_sinapi']})"
            )
    else:
        rank = rank_overlap(rows, top_n=min(5, len(rows)))

    mom_failures = _validate_mom_oscillation(expectations, tol)
    failures.extend(mom_failures)

    return {
        "ok": not failures,
        "failures": failures,
        "aggregate": agg,
        "rank": rank,
        "n_rows": len(rows),
    }


def _validate_mom_oscillation(
    expectations: dict[str, Any],
    tol: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    default_max = float(tol.get("mom_delta_pct_max", 1.0))
    per_uf_max = tol.get("mom_delta_pct_max_por_uf") or {}
    for uf, block in (expectations.get("oscilacao_mensal") or {}).items():
        a = float(block["sinapi_abril_2026"])
        b = float(block["sinapi_maio_2026"])
        mom = (b - a) / a * 100.0
        exp_mom = float(block.get("mom_delta_pct", mom))
        if abs(mom - exp_mom) > 0.05:
            failures.append(f"mom.{uf}: computed {mom:.3f}% != golden {exp_mom}%")
        max_mom = float(per_uf_max.get(uf, default_max))
        if abs(mom) > max_mom:
            failures.append(
                f"mom.{uf}: |delta| {abs(mom):.2f}% > teto {max_mom}% (oscilacao alta)"
            )
    return failures


def format_report_md(rows: list[dict[str, Any]] | None = None) -> str:
    rows = rows or compare_all()
    agg = aggregate_metrics(rows)
    rank = rank_overlap(rows)
    lines = [
        "# Comparativo CUB x SINAPI - golden states",
        "",
        f"**UFs pareadas:** {agg.get('n_ufs', 0)}",
        f"**Ratio CUB/SINAPI:** media {agg.get('ratio_cub_sinapi_mean')} | "
        f"desvio {agg.get('ratio_cub_sinapi_stdev')} | "
        f"faixa [{agg.get('ratio_cub_sinapi_min')} - {agg.get('ratio_cub_sinapi_max')}]",
        f"**Delta% medio (CUB acima SINAPI):** {agg.get('delta_pct_mean')}%",
        f"**Obra adaptacao (SINAPI x {FATOR_OBRA_ADAPTACAO}) / CUB:** "
        f"media {agg.get('obra_pct_cub_mean')}% | fator implicito {agg.get('fator_implicito_cub_mean')}",
        "",
        "## Top 5 custo m2",
        f"- CUB: {', '.join(rank['top_cub'])}",
        f"- SINAPI: {', '.join(rank['top_sinapi'])}",
        f"- Overlap: {rank['overlap']}/5 ({', '.join(rank['overlap_ufs']) or '-'})",
        "",
        "## UFs ancora (piloto CE/PR)",
        "",
        "| UF | CUB | SINAPI | Ratio | Delta% | Obra mid | Obra/CUB% |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    exp = load_expectations()
    for uf in exp.get("ufs_ancora") or []:
        row = next((r for r in rows if r["uf"] == uf), None)
        if not row:
            continue
        pilot = " *" if uf in (exp.get("ufs_piloto_produto") or []) else ""
        lines.append(
            f"| {uf}{pilot} | {row['cub_m2']} | {row['sinapi_m2']} | "
            f"{row['ratio_cub_sinapi']} | {row['delta_pct']}% | "
            f"{row['obra_adaptacao_mid']} | {row['obra_pct_cub']}% |"
        )
    lines.extend([
        "",
        "## Leitura rapida",
        "- CUB sistematicamente **5-8% acima** do SINAPI m2 na mesma UF.",
        "- Ratio CUB/SINAPI **estavel** entre UFs (desvio ~1%).",
        "- Obra adaptacao atual (SINAPI x 0,19) ~ **17,5-18% do CUB** -- trocar regua para CUB x 0,19",
        "  elevaria obra ~**7,5%** sem recalibrar fator.",
        "",
        "*Fontes: `data/cub_pilot/cub_estadual_golden.json` + SINAPI snapshot golden/fixture.*",
    ])
    return "\n".join(lines)
