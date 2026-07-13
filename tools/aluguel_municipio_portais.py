"""Shim — implementação legada em `tools/9_obsolete/`.

Viabilidade = MRLR Tier 0 (`tools/aluguel_mrlr.py`). Este módulo só serve fallback
A4 Tier 1 quando MRLR indisponível. Bundle batch não usa mais `aluguel_portais`.
"""
from __future__ import annotations

import importlib.util
from collections.abc import Coroutine
from pathlib import Path
from typing import Any, Callable

_OBS = Path(__file__).resolve().parent / "9_obsolete" / "aluguel_municipio_portais.py"
_spec = importlib.util.spec_from_file_location("_gymsite_aluguel_portais_obsolete", _OBS)
if _spec is None or _spec.loader is None:
    raise ImportError(f"legado não encontrado: {_OBS}")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

for _name in dir(_mod):
    if _name.startswith("__"):
        continue
    globals()[_name] = getattr(_mod, _name)

# Re-exports explícitos — type checkers não seguem o loop dinâmico acima.
MIN_SAMPLES_ALTA: int = _mod.MIN_SAMPLES_ALTA
MIN_SAMPLES_MEDIA: int = _mod.MIN_SAMPLES_MEDIA
pesquisar_aluguel_municipio: Callable[..., Coroutine[Any, Any, dict[str, Any]]] = (
    _mod.pesquisar_aluguel_municipio
)
pesquisar_aluguel_municipio_sync = _mod.pesquisar_aluguel_municipio_sync
aggregate_municipio = _mod.aggregate_municipio
build_portal_search_urls = _mod.build_portal_search_urls
parse_listings_html = _mod.parse_listings_html
_olx_ad_matches_municipio = _mod._olx_ad_matches_municipio
_build_queries_aluguel = _mod._build_queries_aluguel

__all__ = [
    "MIN_SAMPLES_ALTA",
    "MIN_SAMPLES_MEDIA",
    "pesquisar_aluguel_municipio",
    "pesquisar_aluguel_municipio_sync",
    "aggregate_municipio",
    "build_portal_search_urls",
    "parse_listings_html",
    "_olx_ad_matches_municipio",
    "_build_queries_aluguel",
]
