"""
Benchmarks de empresas fitness listadas (CVM / RI).

Fase B2: batch `cvm_fetch` preenche SMFT3 via ITR; KPIs operacionais (alunos, ARPU)
permanecem no RI — não scrape automático aqui.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / "metrics" / "cache" / "sector_listed.json"

# Fallback mínimo quando batch CVM ainda não rodou (sem Bluefit/BIOM3 — ticker incorreto).
DEFAULT_LISTED: dict[str, Any] = {
    "version": "1.1",
    "fonte": "curadoria_gymsite_fallback",
    "data_coleta": "2026-06-02",
    "empresas": [
        {
            "nome": "Smart Fit",
            "ticker": "SMFT3",
            "periodo_ref": None,
            "fonte": "aguardando batch CVM ITR (tools/cvm_fetch.py)",
            "kpis": {
                "margem_ebitda_pct": None,
                "capex_por_unidade_brl": None,
                "alunos_ativos": None,
                "churn_pct": None,
                "arpu_brl": None,
                "divida_liquida_ebitda": None,
            },
            "notas": "Rodar: python scripts/batch/update_benchmark_snapshots.py --fetch-cvm",
        },
    ],
    "notas_setor": (
        "Bluefit, Bio Ritmo e Bodytech não são comparáveis via B3/CVM como SMFT3; "
        "BIOM3 é BIOMM (farma), não fitness."
    ),
    "links_oficiais": {
        "cvm_dados": "https://dados.cvm.gov.br/dataset/?q=ITR",
        "ri_smartfit": "https://ri.smartfit.com.br/",
    },
}


def _load_snapshot() -> dict[str, Any] | None:
    if not CACHE_PATH.is_file():
        return None
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def save_sector_listed_snapshot(data: dict[str, Any]) -> Path:
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


def obter_sector_listed(*, force_defaults: bool = False) -> dict[str, Any]:
    """Retorna snapshot de redes listadas; nunca levanta exceção."""
    if not force_defaults:
        snap = _load_snapshot()
        if snap and snap.get("empresas"):
            return snap
    return dict(DEFAULT_LISTED)


def empresa_por_ticker(ticker: str) -> dict[str, Any] | None:
    ticker = (ticker or "").strip().upper()
    data = obter_sector_listed()
    for emp in data.get("empresas") or []:
        if isinstance(emp, dict) and (emp.get("ticker") or "").upper() == ticker:
            return emp
    return None


def kpis_smart_fit() -> dict[str, Any]:
    emp = empresa_por_ticker("SMFT3")
    if not emp:
        return {}
    return dict(emp.get("kpis") or {})


def merge_into_benchmark_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Anexa sector_listed ao payload de benchmarks setoriais."""
    out = dict(snapshot)
    out["sector_listed"] = obter_sector_listed()
    return out
