"""
Régua obra A4 — CUB estadual (primário) com fallback SINAPI → benchmark.
"""
from __future__ import annotations

import os
from typing import Any, Literal

ObraRegua = Literal["cub", "sinapi"]

_REGUA_ENV = "OBRA_REGUA"


def obra_regua_policy() -> ObraRegua:
    raw = (os.environ.get(_REGUA_ENV) or "cub").strip().lower()
    return "sinapi" if raw == "sinapi" else "cub"


def _is_benchmark(block: dict[str, Any] | None) -> bool:
    return (block or {}).get("fonte_obra", "").startswith("benchmark_fixo")


def resolve_capex_indices_for_uf(
    uf: str,
    *,
    capex_indices: dict[str, Any] | None = None,
    regua: ObraRegua | None = None,
) -> dict[str, Any] | None:
    """Resolve índices obra para A4 / market_bundle."""
    if capex_indices and not _is_benchmark(capex_indices):
        return capex_indices

    uf = (uf or "").strip().upper()
    if not uf:
        return None

    regua = regua or obra_regua_policy()

    if regua == "cub":
        from tools.cub_indices import cub_indices_for_uf

        block = cub_indices_for_uf(uf)
        if not _is_benchmark(block):
            return block
        from tools.sinapi_indices import capex_indices_for_uf

        sin = capex_indices_for_uf(uf)
        if not _is_benchmark(sin):
            sin = {**sin, "regua": "sinapi", "regua_fallback": "cub→sinapi"}
            return sin
        return None

    from tools.sinapi_indices import capex_indices_for_uf

    block = capex_indices_for_uf(uf)
    if _is_benchmark(block):
        return None
    return {**block, "regua": "sinapi"}


def carimbo_obra_adaptacao(
    capex_indices: dict[str, Any] | None,
    obra_m2: float,
    modelo: str = "mid",
) -> str:
    """Carimbo: valor · base · fonte · janela."""
    if not capex_indices or _is_benchmark(capex_indices):
        return f"{obra_m2:.2f} BRL/m² · adaptação · parametros_metodologia (Sebrae 2024)"
    regua = capex_indices.get("regua") or "sinapi"
    uf = capex_indices.get("uf") or "?"
    periodo = capex_indices.get("periodo_ref") or capex_indices.get("data_coleta") or "n/d"
    fator = capex_indices.get("fator_obra_adaptacao")
    fonte = capex_indices.get("fonte_obra") or regua
    base = "CUB m²" if regua == "cub" else "SINAPI m²"
    if regua == "cub" and capex_indices.get("cub_m2") is not None:
        base = f"CUB {float(capex_indices['cub_m2']):.2f} m²"
    elif capex_indices.get("sinapi_custo_m2") is not None:
        base = f"SINAPI {float(capex_indices['sinapi_custo_m2']):.2f} m²"
    fator_txt = f" · fator {fator}" if fator is not None else ""
    fb = capex_indices.get("regua_fallback")
    fb_txt = f" · fallback {fb}" if fb else ""
    return (
        f"{obra_m2:.2f} BRL/m² · obra {modelo} · {base} × adaptação · "
        f"{fonte} · {uf} · {periodo}{fator_txt}{fb_txt}"
    )
