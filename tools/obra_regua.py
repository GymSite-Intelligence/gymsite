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
    """Compat — delega para carimbo_obra_civil (adaptação)."""
    from tools.obra_capex import carimbo_obra_civil

    return carimbo_obra_civil(
        capex_indices, obra_m2, tipo_obra="adaptacao", modelo=modelo
    )
