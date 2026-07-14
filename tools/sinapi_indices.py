"""
Índices SINAPI (SIDRA tabela 2296) — custo médio m² por UF.

Converte custo de construção civil em proxy de obra de adaptação para academias
(fator fixo ~19% do SINAPI m², calibrado com benchmark mid R$ 350).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / "metrics" / "cache" / "capex_indices.json"

SIDRA_TABLE = 2296
SIDRA_VAR_CUSTO_M2 = 48
SIDRA_URL = (
    f"https://apisidra.ibge.gov.br/values/t/{SIDRA_TABLE}"
    f"/n3/all/v/{SIDRA_VAR_CUSTO_M2}/p/last/f/u"
)

# IBGE N3 → UF (invertido de ibge_tools.CODIGOS_ESTADO)
_N3_TO_UF: dict[str, str] = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL",
    "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP", "41": "PR",
    "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}

# Adaptação comercial/academia ≈ fração do custo m² habitacional SINAPI
FATOR_OBRA_ADAPTACAO = 0.19
_RATIO_LOW_MID = 200.0 / 350.0
_RATIO_PREMIUM_MID = 600.0 / 350.0


def _parse_sidra_rows(payload: list[Any]) -> list[dict[str, Any]]:
    if not payload or len(payload) < 2:
        return []
    rows: list[dict[str, Any]] = []
    for item in payload[1:]:
        if not isinstance(item, dict):
            continue
        n3 = str(item.get("D1C") or "").strip()
        uf = _N3_TO_UF.get(n3)
        if not uf:
            continue
        try:
            valor = float(str(item.get("V") or "").replace(",", "."))
        except ValueError:
            continue
        rows.append(
            {
                "uf": uf,
                "sinapi_custo_m2": valor,
                "periodo": (item.get("D3N") or "").strip(),
                "n3": n3,
            }
        )
    return rows


def fetch_sinapi_custo_m2_por_uf(*, client: httpx.Client | None = None) -> list[dict[str, Any]]:
    own = client is None
    client = client or httpx.Client(timeout=60.0, follow_redirects=True)
    try:
        r = client.get(SIDRA_URL)
        r.raise_for_status()
        return _parse_sidra_rows(r.json())
    finally:
        if own:
            client.close()


def obra_adaptacao_por_modelo(sinapi_custo_m2: float) -> dict[str, float]:
    mid = round(sinapi_custo_m2 * FATOR_OBRA_ADAPTACAO, 2)
    return {
        "low": round(mid * _RATIO_LOW_MID, 2),
        "mid": mid,
        "premium": round(mid * _RATIO_PREMIUM_MID, 2),
    }


def build_capex_snapshot(rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    rows = rows if rows is not None else fetch_sinapi_custo_m2_por_uf()
    por_uf: dict[str, Any] = {}
    periodo = None
    for row in rows:
        uf = row["uf"]
        sinapi = row["sinapi_custo_m2"]
        periodo = periodo or row.get("periodo")
        por_uf[uf] = {
            "sinapi_custo_m2": sinapi,
            "obra_adaptacao_por_m2": obra_adaptacao_por_modelo(sinapi),
            "periodo_ref": row.get("periodo"),
        }
    return {
        "version": "1.0",
        "fonte": "IBGE SIDRA SINAPI tabela 2296",
        "data_coleta": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "periodo_ref": periodo,
        "fator_obra_adaptacao": FATOR_OBRA_ADAPTACAO,
        "por_uf": por_uf,
    }


def save_capex_snapshot(data: dict[str, Any]) -> Path:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        **data,
        "_cached_at_iso": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    CACHE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return CACHE_PATH


def load_capex_snapshot() -> dict[str, Any] | None:
    if not CACHE_PATH.is_file():
        return None
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def capex_indices_for_uf(uf: str) -> dict[str, Any]:
    """Bloco para market_bundle.capex_indices."""
    uf = (uf or "").strip().upper()
    snap = load_capex_snapshot()
    if not snap or not snap.get("por_uf"):
        return {"uf": uf, "fonte_obra": "benchmark_fixo_fase_a"}
    block = (snap.get("por_uf") or {}).get(uf)
    if not block:
        return {
            "uf": uf,
            "fonte_obra": "benchmark_fixo_fase_a",
            "aviso": f"SINAPI sem UF {uf} no snapshot",
        }
    obra = block.get("obra_adaptacao_por_m2") or {}
    return {
        "uf": uf,
        "regua": "sinapi",
        "fonte_obra": snap.get("fonte", "SINAPI"),
        "periodo_ref": block.get("periodo_ref") or snap.get("periodo_ref"),
        "sinapi_custo_m2": block.get("sinapi_custo_m2"),
        "obra_adaptacao_por_m2": obra.get("mid"),
        "obra_adaptacao_por_m2_por_modelo": obra,
    }


def atualizar_capex_indices() -> dict[str, Any]:
    snap = build_capex_snapshot()
    save_capex_snapshot(snap)
    return snap
