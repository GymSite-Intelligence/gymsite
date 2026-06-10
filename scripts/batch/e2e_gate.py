"""
E2E gate — valida trilha bundle + skip Deep Research sem API completa.

Chamado apos cada etapa em run_stage_tests.py (--e2e, default ligado).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

E2E_CIDADE = "Fortaleza"
E2E_BAIRRO = "Meireles"
E2E_UF = "CE"

STAGE_ORDER = (
    "a1_ckan",
    "a2_cvm",
    "a3_benchmarks",
    "a4_bundle",
    "a5_integration",
    "a6_e2e",
    "b1_bairro",
    "b2_cvm",
    "b3_sinapi",
    "c1_golden_bundle_a0",
    "c2_curadoria",
    "c3_airflow_dag",
)


def _fail(msg: str) -> int:
    print(f"[E2E FAIL] {msg}")
    return 1


def _ok(msg: str) -> None:
    print(f"[E2E OK] {msg}")


def check_a1_ckan() -> int:
    from tools.ckan_client import discover_demografia_queries, package_search

    qs = discover_demografia_queries(E2E_CIDADE, E2E_UF)
    if len(qs) < 2:
        return _fail("discover_demografia_queries vazio")
    _ok(f"ckan queries={len(qs)}")
    return 0


def check_a2_cvm() -> int:
    from tools.cvm_listed_metrics import empresa_por_ticker, obter_sector_listed

    data = obter_sector_listed()
    if not data.get("empresas"):
        return _fail("sector_listed sem empresas")
    if not empresa_por_ticker("SMFT3"):
        return _fail("SMFT3 ausente")
    _ok("sector_listed SMFT3")
    return 0


def check_a3_benchmarks() -> int:
    from tools.benchmarks_tool import obter_benchmarks_setoriais

    snap_path = ROOT / "metrics" / "cache" / "benchmark_snapshots.json"
    if not snap_path.is_file():
        return _fail("benchmark_snapshots.json ausente")
    bench = obter_benchmarks_setoriais()
    tpm = bench.get("ticket_por_modelo") or {}
    if not tpm.get("low"):
        return _fail("benchmarks sem ticket_por_modelo.low")
    _ok(f"benchmarks fonte={bench.get('fonte', 'n/d')[:60]}")
    return 0


def _ensure_bundle(*, rebuild: bool) -> int:
    from tools.market_bundle import bundle_is_fresh, load_market_bundle

    bundle = load_market_bundle(E2E_CIDADE, E2E_BAIRRO, E2E_UF)
    if bundle and bundle_is_fresh(bundle) and not rebuild:
        return 0
    from scripts.batch.build_market_bundles import build_bundle
    from tools.market_bundle import save_market_bundle

    print("[E2E] build_market_bundles (skip-ckan)...")
    data = build_bundle(E2E_CIDADE, E2E_BAIRRO, E2E_UF, skip_ckan=True)
    save_market_bundle(E2E_CIDADE, E2E_BAIRRO, E2E_UF, data)
    return 0


def check_a4_bundle(*, rebuild: bool = False) -> int:
    from tools.market_bundle import (
        bundle_is_fresh,
        carregar_market_bundle,
        inject_market_bundle_context,
        load_market_bundle,
    )

    rc = _ensure_bundle(rebuild=rebuild)
    if rc != 0:
        return rc

    bundle = load_market_bundle(E2E_CIDADE, E2E_BAIRRO, E2E_UF)
    if not bundle or not bundle_is_fresh(bundle):
        return _fail("bundle ausente ou expirado")

    md = carregar_market_bundle(E2E_CIDADE, E2E_BAIRRO, E2E_UF)
    if "status=missing" in md:
        return _fail("carregar_market_bundle missing")

    ctx = inject_market_bundle_context(E2E_CIDADE, E2E_BAIRRO, E2E_UF, {})
    if not ctx.get("market_bundle_available"):
        return _fail("inject_market_bundle_context falhou")

    ibge = (bundle.get("local") or {}).get("codigo_ibge_municipio")
    if not ibge:
        return _fail("bundle sem codigo_ibge_municipio")

    _ok(f"bundle ibge={ibge} briefing_len={len(md)}")
    return 0


def check_a4_dr_skip() -> int:
    """Deep Research deve retornar em <3s quando skip_deep_research no contexto."""
    from tools.enrichment_cache import (
        reset_pipeline_enrichment_context,
        set_pipeline_enrichment_context,
    )
    from tools.market_bundle import carregar_market_bundle, inject_market_bundle_context
    from tools.deep_research_tool import rodar_deep_research

    md = carregar_market_bundle(E2E_CIDADE, E2E_BAIRRO, E2E_UF)
    if "status=missing" in md:
        return _fail("DR skip: bundle missing")

    ctx = inject_market_bundle_context(E2E_CIDADE, E2E_BAIRRO, E2E_UF, {})
    ctx["skip_deep_research"] = True
    ctx["market_bundle_briefing_md"] = md

    token = set_pipeline_enrichment_context(ctx)
    try:
        t0 = time.perf_counter()
        out = rodar_deep_research(E2E_CIDADE, E2E_BAIRRO)
        elapsed = time.perf_counter() - t0
    finally:
        reset_pipeline_enrichment_context(token)

    if "market_bundle" not in out and "Briefing de mercado (market_bundle)" not in out:
        return _fail("DR skip nao retornou conteudo do bundle")
    if elapsed > 5.0:
        return _fail(f"DR skip lento demais: {elapsed:.2f}s (esperado <5s)")
    _ok(f"DR skip em {elapsed:.2f}s")
    return 0


def check_a5_integration() -> int:
    from tools.enrichment_cache import inject_cache_context, reset_pipeline_enrichment_context, set_pipeline_enrichment_context
    from tools.market_bundle import inject_market_bundle_context

    ctx = inject_cache_context(E2E_CIDADE, E2E_BAIRRO, E2E_UF, {})
    ctx = inject_market_bundle_context(E2E_CIDADE, E2E_BAIRRO, E2E_UF, ctx)
    token = set_pipeline_enrichment_context(ctx)
    try:
        if not ctx.get("market_bundle_available") and not ctx.get("enrichment_cache"):
            return _fail("pipeline ctx sem bundle nem enrichment cache")
        from tools.financial_tools import calcular_viabilidade_3_cenarios

        fin = calcular_viabilidade_3_cenarios(
            cidade=E2E_CIDADE,
            bairro=E2E_BAIRRO,
            uf=E2E_UF,
            area_m2=1000,
            aluguel_mensal=35000,
            tamanho_preset="m",
        )
        if not fin.get("cenarios"):
            return _fail("viabilidade_3_cenarios sem cenarios")
        _ok(f"viabilidade cenarios={len(fin.get('cenarios') or {})}")
    finally:
        reset_pipeline_enrichment_context(token)
    return 0


def check_b2_cvm_smft3() -> int:
    from tools.cvm_listed_metrics import empresa_por_ticker

    emp = empresa_por_ticker("SMFT3")
    if not emp:
        return _fail("SMFT3 ausente no sector_listed")
    fonte = (emp.get("fonte") or "").upper()
    kpis = emp.get("kpis") or {}
    if "CVM ITR" in fonte:
        if kpis.get("margem_ebitda_pct") is None:
            return _fail("SMFT3 com fonte CVM mas sem margem_ebitda_pct")
        _ok(
            f"SMFT3 CVM periodo={emp.get('periodo_ref')} "
            f"margem={kpis.get('margem_ebitda_pct')}%"
        )
    else:
        _ok("SMFT3 ok (rode --fetch-cvm para metricas ITR)")
    return 0


def check_b3_sinapi_bundle() -> int:
    from tools.market_bundle import load_market_bundle

    bundle = load_market_bundle(E2E_CIDADE, E2E_BAIRRO, E2E_UF)
    if not bundle:
        return _fail("bundle ausente para check b3")
    capex = bundle.get("capex_indices") or {}
    if (capex.get("fonte_obra") or "").startswith("benchmark_fixo"):
        _ok("capex_indices fallback (rode update_capex_indices no batch)")
        return 0
    if not capex.get("obra_adaptacao_por_m2"):
        return _fail("capex_indices sem obra_adaptacao_por_m2")
    _ok(f"sinapi obra_mid={capex.get('obra_adaptacao_por_m2')} periodo={capex.get('periodo_ref')}")
    return 0


def check_b1_bairro_meireles() -> int:
    from tools.market_bundle import load_market_bundle

    bundle = load_market_bundle(E2E_CIDADE, E2E_BAIRRO, E2E_UF)
    if not bundle:
        return _fail("bundle ausente para check b1")
    b = (bundle.get("demografia") or {}).get("bairro") or {}
    if b.get("renda_media") is None:
        return _fail("renda_media_bairro ainda null (rode build_market_bundles)")
    missing = bundle.get("missing_fields") or []
    if "renda_media_bairro" in missing:
        return _fail("missing_fields ainda contem renda_media_bairro")
    _ok(f"renda_bairro={b.get('renda_media')} fonte={b.get('fonte')}")
    return 0


def check_a6_full(*, rebuild_bundle: bool = False) -> int:
    for fn in (
        check_a1_ckan,
        check_a2_cvm,
        check_a3_benchmarks,
        lambda: check_a4_bundle(rebuild=rebuild_bundle),
        check_a4_dr_skip,
        check_a5_integration,
    ):
        if fn() != 0:
            return 1
    return 0


_STAGE_CHECKS: dict[str, list[Callable[..., int]]] = {
    "a1_ckan": [check_a1_ckan],
    "a2_cvm": [check_a1_ckan, check_a2_cvm],
    "a3_benchmarks": [check_a1_ckan, check_a2_cvm, check_a3_benchmarks],
    "a4_bundle": [check_a1_ckan, check_a2_cvm, check_a3_benchmarks, lambda: check_a4_bundle(rebuild=False), check_a4_dr_skip],
    "a5_integration": [check_a6_full],
    "a6_e2e": [check_a6_full],
    "b1_bairro": [
        check_a1_ckan,
        check_a2_cvm,
        check_a3_benchmarks,
        check_a4_bundle,
        check_b1_bairro_meireles,
    ],
    "b2_cvm": [
        check_a1_ckan,
        check_a2_cvm,
        check_b2_cvm_smft3,
    ],
    "b3_sinapi": [
        check_a1_ckan,
        check_b3_sinapi_bundle,
    ],
    "c1_golden_bundle_a0": [
        check_a1_ckan,
        check_a2_cvm,
        lambda: check_a4_bundle(rebuild=False),
        check_a4_dr_skip,
    ],
    "c2_curadoria": [
        check_a1_ckan,
        check_b3_sinapi_bundle,
    ],
    "c3_airflow_dag": [],
}


def run_e2e_for_stage(stage_id: str, *, rebuild_bundle: bool = False) -> int:
    if stage_id not in _STAGE_CHECKS:
        return 0
    print(f"\n--- E2E gate pos-{stage_id} ---")
    for fn in _STAGE_CHECKS[stage_id]:
        if fn is check_a4_bundle:
            rc = check_a4_bundle(rebuild=rebuild_bundle)
        elif fn is check_a6_full:
            rc = check_a6_full(rebuild_bundle=rebuild_bundle)
        else:
            rc = fn()
        if rc != 0:
            return rc
    print(f"--- E2E pos-{stage_id} PASS ---\n")
    return 0
