#!/usr/bin/env python3
"""
Gate de testes por etapa — rodar após cada mudança de código no pipeline de dados.

Uso:
  python scripts/batch/run_stage_tests.py --list
  python scripts/batch/run_stage_tests.py --stage a1_ckan
  python scripts/batch/run_stage_tests.py --stage all
  python scripts/batch/run_stage_tests.py --stage all --with-batch   # reexecuta batch + valida artefatos
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STAGES: dict[str, dict] = {
    "a1_ckan": {
        "title": "CKAN client (descoberta)",
        "pytest": ["tools/test_ckan_client.py"],
        "artifacts": [],
    },
    "a2_cvm": {
        "title": "CVM / sector_listed",
        "pytest": ["tools/test_cvm_listed_metrics.py"],
        "artifacts": [],
    },
    "a3_benchmarks": {
        "title": "Benchmark snapshots",
        "pytest": [],
        "artifacts": ["metrics/cache/benchmark_snapshots.json", "metrics/cache/sector_listed.json"],
        "batch": ["scripts/batch/update_benchmark_snapshots.py"],
    },
    "a4_bundle": {
        "title": "market_bundle build + loader",
        "pytest": ["tools/test_market_bundle.py"],
        "artifacts": ["data/market_bundles/fortaleza_meireles_CE.json"],
        "batch": [
            "scripts/batch/build_market_bundles.py",
            "--cidade",
            "Fortaleza",
            "--bairro",
            "Meireles",
            "--uf",
            "CE",
            "--skip-ckan",
        ],
    },
    "a5_integration": {
        "title": "Integração API/A0/DR skip (imports)",
        "pytest": [
            "tools/test_market_bundle.py",
            "tools/test_enrichment_cache.py",
            "tools/test_ckan_client.py",
            "tools/test_cvm_listed_metrics.py",
        ],
        "artifacts": [],
        "import_checks": [
            "tools.market_bundle:carregar_market_bundle",
            "tools.benchmarks_tool:obter_benchmarks_setoriais",
            "agents.a0_context_builder:context_builder_agent",
        ],
    },
    "a6_e2e": {
        "title": "E2E pipeline (bundle + DR skip + viabilidade)",
        "pytest": ["tools/test_e2e_market_pipeline.py"],
        "artifacts": ["data/market_bundles/fortaleza_meireles_CE.json"],
    },
    "b1_bairro": {
        "title": "Renda por bairro (piloto curado)",
        "pytest": ["tools/test_bairro_renda_loader.py"],
        "artifacts": ["data/bairro_renda_pilot/fortaleza_ce.json"],
        "batch": [
            "scripts/batch/build_market_bundles.py",
            "--cidade",
            "Fortaleza",
            "--bairro",
            "Meireles",
            "--uf",
            "CE",
            "--skip-ckan",
        ],
    },
    "b2_cvm": {
        "title": "CVM ITR fetch SMFT3 (B2)",
        "pytest": ["tools/test_cvm_fetch.py", "tools/test_cvm_listed_metrics.py"],
        "artifacts": [],
        "batch": ["scripts/batch/update_benchmark_snapshots.py", "--fetch-cvm"],
    },
    "b3_sinapi": {
        "title": "SINAPI/SIDRA capex por UF (B3)",
        "pytest": ["tools/test_sinapi_indices.py"],
        "artifacts": ["metrics/cache/capex_indices.json"],
        "batch": ["scripts/batch/update_capex_indices.py"],
    },
    "c1_golden_bundle_a0": {
        "title": "Fase C — A0 bundle-only (sem DR)",
        "pytest": ["tools/test_fase_c.py"],
        "artifacts": ["data/market_bundles/fortaleza_meireles_CE.json"],
        "batch": ["scripts/batch/golden_bundle_a0_gate.py", "--wave", "red"],
    },
    "c2_curadoria": {
        "title": "Fase C — franquias + legal fees piloto",
        "pytest": ["tools/test_fase_c.py"],
        "artifacts": [
            "data/franchise_curated/fitness_br.json",
            "data/legal_fees_pilot/fortaleza_ce.json",
        ],
    },
    "c3_airflow_dag": {
        "title": "Fase C — DAG Airflow (sintaxe)",
        "pytest": ["tools/test_fase_c.py::test_airflow_dag_file_parses"],
    },
}

STAGE_SEQUENCE = (
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


def _run_pytest(paths: list[str]) -> int:
    if not paths:
        return 0
    cmd = [sys.executable, "-m", "pytest", *paths, "-q", "--tb=short"]
    print(">", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(ROOT))


def _run_batch(script_args: list[str]) -> int:
    cmd = [sys.executable, *script_args]
    print(">", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(ROOT))


def _validate_artifact(rel_path: str) -> tuple[bool, str]:
    path = ROOT / rel_path
    if not path.is_file():
        return False, f"arquivo ausente: {rel_path}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"JSON inválido {rel_path}: {exc}"
    if "benchmark_snapshots" in rel_path:
        if not isinstance(data.get("setorial"), dict):
            return False, "benchmark_snapshots sem setorial"
    if "market_bundles" in rel_path:
        if not data.get("gerado_em"):
            return False, "bundle sem gerado_em"
        if not (data.get("local") or {}).get("codigo_ibge_municipio"):
            return False, "bundle sem codigo_ibge_municipio"
    if "bairro_renda_pilot" in rel_path:
        if not data.get("bairros"):
            return False, "piloto sem bairros"
    if "capex_indices" in rel_path:
        if not data.get("por_uf"):
            return False, "capex_indices sem por_uf"
    return True, "ok"


def _import_check(spec: str) -> tuple[bool, str]:
    mod_name, attr = spec.split(":", 1)
    try:
        import importlib

        mod = importlib.import_module(mod_name)
        if not hasattr(mod, attr):
            return False, f"{spec} não encontrado"
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def run_stage(stage_id: str, *, with_batch: bool, run_e2e: bool = True) -> int:
    cfg = STAGES.get(stage_id)
    if not cfg:
        print(f"stage desconhecido: {stage_id}")
        return 2

    print(f"\n=== {stage_id}: {cfg['title']} ===\n")
    rc = 0

    if with_batch and cfg.get("batch"):
        if _run_batch(cfg["batch"]) != 0:
            return 1

    rc = _run_pytest(cfg.get("pytest") or [])
    if rc != 0:
        return rc

    for spec in cfg.get("import_checks") or []:
        ok, msg = _import_check(spec)
        print(f"import {spec}: {msg}")
        if not ok:
            return 1

    for art in cfg.get("artifacts") or []:
        ok, msg = _validate_artifact(art)
        print(f"artifact {art}: {msg}")
        if not ok:
            return 1

    print(f"\n[PASS] {stage_id}\n")

    if run_e2e:
        from scripts.batch.e2e_gate import run_e2e_for_stage

        if run_e2e_for_stage(stage_id, rebuild_bundle=with_batch) != 0:
            return 1

    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Test gates por etapa (market data Fase A+)")
    p.add_argument("--stage", default="all", help="id da etapa ou 'all'")
    p.add_argument("--list", action="store_true", help="lista etapas")
    p.add_argument(
        "--with-batch",
        action="store_true",
        help="reexecuta scripts batch antes de validar artefatos (rede)",
    )
    p.add_argument(
        "--no-e2e",
        action="store_true",
        help="nao roda E2E gate apos cada etapa",
    )
    p.add_argument(
        "--e2e-only",
        action="store_true",
        help="so executa a6_e2e / e2e_gate",
    )
    args = p.parse_args()

    if args.list:
        for sid in STAGE_SEQUENCE:
            cfg = STAGES[sid]
            print(f"  {sid}: {cfg['title']}")
        return 0

    if args.e2e_only:
        from scripts.batch.e2e_gate import run_e2e_for_stage

        return run_e2e_for_stage("a6_e2e", rebuild_bundle=args.with_batch)

    run_e2e = not args.no_e2e

    if args.stage == "all":
        for sid in STAGE_SEQUENCE:
            if run_stage(sid, with_batch=args.with_batch, run_e2e=run_e2e) != 0:
                return 1
        print("=== ALL STAGES PASS ===")
        return 0

    return run_stage(args.stage, with_batch=args.with_batch, run_e2e=run_e2e)


if __name__ == "__main__":
    raise SystemExit(main())
