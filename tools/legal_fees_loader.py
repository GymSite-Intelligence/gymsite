"""Taxas municipais / CAU — piloto curado (Fase C)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parent.parent
PILOT_DIR = ROOT / "data" / "legal_fees_pilot"

FaixaPolicy = Literal["min", "mid", "max", "typico"]


def _slug(cidade: str, uf: str) -> str:
    c = re.sub(r"[^a-z0-9]+", "_", (cidade or "").lower()).strip("_")
    return f"{c}_{(uf or '').lower()}"


def load_legal_fees(cidade: str, uf: str) -> dict[str, Any] | None:
    path = PILOT_DIR / f"{_slug(cidade, uf)}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def bloco_para_bundle(cidade: str, uf: str) -> dict[str, Any]:
    data = load_legal_fees(cidade, uf)
    if not data:
        return {
            "disponivel": False,
            "cidade": cidade,
            "uf": uf.upper(),
            "fonte": None,
        }
    return {
        "disponivel": True,
        "cidade": data.get("cidade", cidade),
        "uf": data.get("uf", uf.upper()),
        "fonte": data.get("fonte"),
        "data_coleta": data.get("data_coleta"),
        "taxas": data.get("taxas") or {},
        "prazo_meses_tipico": data.get("prazo_meses_tipico") or {},
        "notas": data.get("notas"),
    }


def _pick_faixa(block: dict[str, Any] | None, policy: FaixaPolicy = "mid") -> float:
    if not block or not isinstance(block, dict):
        return 0.0
    mn = float(block.get("min") or 0)
    mx = float(block.get("max") if block.get("max") is not None else mn)
    typico = block.get("typico")
    if policy == "typico" and typico is not None:
        return round(float(typico), 2)
    if policy == "min":
        return round(mn, 2)
    if policy == "max":
        return round(mx, 2)
    if typico is not None:
        return round(float(typico), 2)
    if mn == mx:
        return round(mn, 2)
    return round((mn + mx) / 2.0, 2)


def _projeto_arquitetonico_brl(
    block: dict[str, Any] | None,
    area_m2: float,
    policy: FaixaPolicy = "mid",
) -> float:
    if not block or not isinstance(block, dict):
        return 0.0
    r_m2 = block.get("r_m2")
    if isinstance(r_m2, dict) and area_m2 > 0:
        rate = _pick_faixa(r_m2, policy)
        raw = rate * area_m2
        lo = float(block.get("min") or 0)
        hi = float(block.get("max") or raw)
        if hi > 0 and lo > 0:
            return round(max(lo, min(raw, hi)), 2)
        return round(raw, 2)
    return _pick_faixa(block, policy)


def resolver_taxas_capex(
    cidade: str,
    uf: str,
    area_m2: float,
    *,
    policy: FaixaPolicy = "mid",
) -> dict[str, Any] | None:
    """Resolve alvará/licenças + projeto para `_calcular_capex_detalhado`."""
    data = load_legal_fees(cidade, uf)
    if not data:
        return None

    taxas = data.get("taxas") or {}
    alvara = _pick_faixa(taxas.get("alvara_funcionamento_brl"), policy)
    bombeiros = _pick_faixa(taxas.get("taxa_bombeiros_brl"), policy)
    sanit = _pick_faixa(taxas.get("vistoria_sanitaria_brl"), policy)
    alvara_e_taxas = round(alvara + bombeiros + sanit, 2)
    projeto = _projeto_arquitetonico_brl(
        taxas.get("projeto_arquitetonico_cau_brl"), area_m2, policy
    )

    fonte = data.get("fonte") or "legal_fees_pilot"
    coleta = data.get("data_coleta") or "n/d"
    carimbo_alvara = (
        f"{alvara_e_taxas:.2f} BRL · alvará+bombeiros+sanitária · {fonte} · {coleta}"
    )
    carimbo_projeto = (
        f"{projeto:.2f} BRL · projeto CAU · {fonte} · {coleta} · policy={policy}"
    )

    return {
        "disponivel": True,
        "cidade": data.get("cidade", cidade),
        "uf": (data.get("uf") or uf or "").upper(),
        "fonte": fonte,
        "data_coleta": coleta,
        "policy": policy,
        "alvara_e_taxas": alvara_e_taxas,
        "projeto_arquitetonico": projeto,
        "detalhe_taxas": {
            "alvara_funcionamento_brl": alvara,
            "taxa_bombeiros_brl": bombeiros,
            "vistoria_sanitaria_brl": sanit,
        },
        "carimbo_alvara_e_taxas": carimbo_alvara,
        "carimbo_projeto_arquitetonico": carimbo_projeto,
    }
