"""
Árvore obra civil A4 — adaptação vs bruta sobre CUB/SINAPI/benchmark.
"""
from __future__ import annotations

from typing import Any, Literal

from tools.parametros_metodologia import param_por_modelo
from tools.sinapi_indices import FATOR_OBRA_ADAPTACAO, obra_adaptacao_por_modelo

TipoObra = Literal["adaptacao", "bruta"]

# Shell comercial novo ≈ 58% CUB m² (estrutura + instalações base).
FATOR_OBRA_BRUTA = 0.58

_RATIO_LOW_MID = 200.0 / 350.0
_RATIO_PREMIUM_MID = 600.0 / 350.0

_LINHA_BY_TIPO: dict[TipoObra, str] = {
    "adaptacao": "obra_adaptacao",
    "bruta": "obra_bruta",
}


def normalize_tipo_obra(raw: str | None) -> TipoObra:
    v = (raw or "adaptacao").strip().lower()
    if v in ("bruta", "obra_bruta", "shell", "zero", "novo", "ground_up"):
        return "bruta"
    return "adaptacao"


def fator_obra(tipo_obra: TipoObra) -> float:
    return FATOR_OBRA_BRUTA if tipo_obra == "bruta" else FATOR_OBRA_ADAPTACAO


def linha_obra(tipo_obra: TipoObra) -> str:
    return _LINHA_BY_TIPO[tipo_obra]


def _benchmark_obra_m2(modelo: str, tipo_obra: TipoObra) -> float:
    base = param_por_modelo("capex_obra_m2")
    mid = float(base.get("mid") or 350.0)
    if tipo_obra == "bruta":
        mid = round(mid * (FATOR_OBRA_BRUTA / FATOR_OBRA_ADAPTACAO), 2)
    ratios = {"low": _RATIO_LOW_MID, "premium": _RATIO_PREMIUM_MID}
    modelo = (modelo or "mid").lower()
    if modelo == "mid":
        return mid
    if modelo in ratios:
        return round(mid * ratios[modelo], 2)
    return mid


def obra_m2_por_modelo(
    modelo: str,
    *,
    tipo_obra: TipoObra = "adaptacao",
    capex_indices: dict[str, Any] | None = None,
) -> float:
    """R$/m² obra civil por modelo e tipo."""
    modelo = (modelo or "mid").lower()
    fator = fator_obra(tipo_obra)

    if capex_indices and not (capex_indices.get("fonte_obra") or "").startswith(
        "benchmark_fixo"
    ):
        if tipo_obra == "adaptacao":
            por_mod = capex_indices.get("obra_adaptacao_por_m2_por_modelo")
            if isinstance(por_mod, dict) and por_mod.get(modelo) is not None:
                return float(por_mod[modelo])
            mid = capex_indices.get("obra_adaptacao_por_m2")
            if mid is not None:
                if modelo == "mid":
                    return float(mid)
                ratios = {"low": _RATIO_LOW_MID, "premium": _RATIO_PREMIUM_MID}
                if modelo in ratios:
                    return round(float(mid) * ratios[modelo], 2)

        idx_m2 = capex_indices.get("cub_m2") or capex_indices.get("sinapi_custo_m2")
        if idx_m2 is not None:
            mid = round(float(idx_m2) * fator, 2)
            por_mod = obra_adaptacao_por_modelo(float(idx_m2))
            if tipo_obra == "bruta":
                por_mod = {
                    "low": round(mid * _RATIO_LOW_MID, 2),
                    "mid": mid,
                    "premium": round(mid * _RATIO_PREMIUM_MID, 2),
                }
            if por_mod.get(modelo) is not None:
                return float(por_mod[modelo])

    return _benchmark_obra_m2(modelo, tipo_obra)


def carimbo_obra_civil(
    capex_indices: dict[str, Any] | None,
    obra_m2: float,
    *,
    tipo_obra: TipoObra = "adaptacao",
    modelo: str = "mid",
) -> str:
    """Carimbo: valor · base · fonte · janela."""
    rotulo = "bruta" if tipo_obra == "bruta" else "adaptação"
    if not capex_indices or (capex_indices.get("fonte_obra") or "").startswith(
        "benchmark_fixo"
    ):
        return (
            f"{obra_m2:.2f} BRL/m² · obra {rotulo} · parametros_metodologia (Sebrae 2024)"
        )

    regua = capex_indices.get("regua") or "sinapi"
    uf = capex_indices.get("uf") or "?"
    periodo = capex_indices.get("periodo_ref") or capex_indices.get("data_coleta") or "n/d"
    fator = fator_obra(tipo_obra)
    fonte = capex_indices.get("fonte_obra") or regua
    if regua == "cub" and capex_indices.get("cub_m2") is not None:
        base = f"CUB {float(capex_indices['cub_m2']):.2f} m²"
    elif capex_indices.get("sinapi_custo_m2") is not None:
        base = f"SINAPI {float(capex_indices['sinapi_custo_m2']):.2f} m²"
    else:
        base = "CUB m²" if regua == "cub" else "SINAPI m²"
    fb = capex_indices.get("regua_fallback")
    fb_txt = f" · fallback {fb}" if fb else ""
    return (
        f"{obra_m2:.2f} BRL/m² · obra {modelo}/{rotulo} · {base} × fator {fator} · "
        f"{fonte} · {uf} · {periodo}{fb_txt}"
    )
