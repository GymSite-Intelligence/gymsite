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
# Curadoria RI (#2): KPIs operacionais que o CVM ITR não traz (vivem no release).
RI_OVERLAY_PATH = ROOT / "metrics" / "cache" / "sector_listed_ri_overlay.json"

# KPIs operacionais — origem RI/release, não CVM ITR. Cobertura monitorada (alerta).
OPERATIONAL_KPIS: tuple[str, ...] = (
    "alunos_ativos",
    "arpu_brl",
    "churn_pct",
    "capex_por_unidade_brl",
)

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


def _load_ri_overlay() -> dict[str, Any]:
    """Curadoria RI de KPIs operacionais por ticker (estrutura: empresas[TICKER].kpis)."""
    if not RI_OVERLAY_PATH.is_file():
        return {}
    try:
        data = json.loads(RI_OVERLAY_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _aplicar_ri_overlay(data: dict[str, Any]) -> dict[str, Any]:
    """Preenche KPIs operacionais null com curadoria RI (não sobrescreve CVM)."""
    overlay = _load_ri_overlay()
    empresas_ov = (overlay.get("empresas") or {}) if overlay else {}
    if not empresas_ov:
        return data
    for emp in data.get("empresas") or []:
        if not isinstance(emp, dict):
            continue
        ov = empresas_ov.get((emp.get("ticker") or "").upper())
        if not ov:
            continue
        kpis = emp.setdefault("kpis", {})
        for k, v in (ov.get("kpis") or {}).items():
            if v is not None and kpis.get(k) is None:
                kpis[k] = v
        emp["kpis_operacionais_fonte"] = overlay.get("fonte")
        emp["kpis_operacionais_periodo"] = ov.get("periodo_ref")
        if ov.get("contexto"):
            emp["contexto_ri"] = ov["contexto"]
    return data


def obter_sector_listed(*, force_defaults: bool = False) -> dict[str, Any]:
    """Retorna snapshot de redes listadas; nunca levanta exceção.

    CVM ITR cobre financeiro; KPIs operacionais (alunos/ARPU/churn) vêm da
    curadoria RI overlay quando disponível. Cobertura é monitorada por
    `sector_kpi_coverage` / `sector_kpi_alertas`.
    """
    if not force_defaults:
        snap = _load_snapshot()
        if snap and snap.get("empresas"):
            return _aplicar_ri_overlay(dict(snap))
    return _aplicar_ri_overlay(dict(DEFAULT_LISTED))


def sector_kpi_coverage(empresa: dict[str, Any]) -> dict[str, Any]:
    """Cobertura de KPIs operacionais (RI) de uma empresa — para alerta/monitor."""
    kpis = (empresa or {}).get("kpis") or {}
    faltando = [k for k in OPERATIONAL_KPIS if kpis.get(k) is None]
    preenchidos = [k for k in OPERATIONAL_KPIS if kpis.get(k) is not None]
    total = len(OPERATIONAL_KPIS)
    return {
        "ticker": (empresa or {}).get("ticker"),
        "total": total,
        "preenchidos": len(preenchidos),
        "pct": round(100.0 * len(preenchidos) / total, 1) if total else 0.0,
        "faltando": faltando,
    }


def sector_kpi_alertas(data: dict[str, Any] | None = None) -> list[str]:
    """Alertas quando KPIs operacionais não estão 100% — driva fechamento via RI overlay."""
    data = data or obter_sector_listed()
    alertas: list[str] = []
    for emp in data.get("empresas") or []:
        if not isinstance(emp, dict):
            continue
        cov = sector_kpi_coverage(emp)
        if cov["pct"] < 100.0:
            alertas.append(
                f"⚠️ KPIs operacionais {cov['ticker']} em {cov['pct']:.0f}% "
                f"({cov['preenchidos']}/{cov['total']}) — faltam {', '.join(cov['faltando'])}. "
                f"Preencher metrics/cache/sector_listed_ri_overlay.json com RI ({emp.get('kpis_operacionais_fonte') or 'ri.smartfit.com.br'})."
            )
    return alertas


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
