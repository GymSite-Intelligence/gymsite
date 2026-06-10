#!/usr/bin/env python3
"""
Dispara cenários do Market Atlas (data/market_waves.csv).

Modos:
  api    — POST /api/relatorios (Redis worker na API deve estar ativo)
  local  — roda pipeline ADK nesta máquina (sequencial)
  stub   — só cria stub + market_wave no Supabase

Uso:
  python scripts/run_market_wave.py --wave red --dry-run
  python scripts/run_market_wave.py --wave red --mode api --limit 1
  python scripts/run_market_wave.py --id fortaleza_parangaba_red_w1 --mode local
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

WAVES_CSV = ROOT / "data" / "market_waves.csv"
GOLDEN_ROOT = ROOT / "eval" / "golden_dataset"
RUNS_DIR = ROOT / "data" / "market_waves_runs"


def _load_scenarios(
    *,
    wave: str | None,
    scenario_id: str | None,
    limit: int | None,
    allow_city_wide: bool,
) -> list[dict[str, str]]:
    if not WAVES_CSV.is_file():
        raise SystemExit(f"Catálogo ausente: {WAVES_CSV}")

    rows: list[dict[str, str]] = []
    with WAVES_CSV.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if scenario_id and row["id"] != scenario_id:
                continue
            if wave and row["wave"] != wave:
                continue
            if not allow_city_wide and row["bairro"].strip().lower() == row["cidade"].strip().lower():
                continue
            rows.append(row)

    if limit is not None:
        rows = rows[:limit]
    return rows


def _input_from_scenario(row: dict[str, str]) -> dict[str, Any]:
    anchor = (row.get("golden_anchor") or "").strip()
    if anchor:
        golden_path = GOLDEN_ROOT / anchor / "input.json"
        if golden_path.is_file():
            return json.loads(golden_path.read_text(encoding="utf-8"))

    return {
        "cidade": row["cidade"],
        "bairro": row["bairro"],
        "uf": row["uf"],
        "area_m2_min": 800,
        "area_m2_max": 1500,
        "tamanho_preset": "m",
        "publico_alvo": "25-40",
        "genero_alvo": "misto",
        "tipo_negocio": "academia",
        "estacionamento_obrigatorio": True,
        "bairros_indicados": [],
    }


def _poll_done(uuid: str, *, interval: int, timeout: int) -> dict[str, Any]:
    from tools.postgrest_sb import fetch_relatorio_status

    t0 = time.time()
    while time.time() - t0 < timeout:
        row = fetch_relatorio_status(uuid)
        if not row:
            raise RuntimeError(f"Relatório {uuid} não encontrado")
        st = row.get("status")
        print(f"    poll status={st} tempo={row.get('tempo_execucao_segundos')}s", flush=True)
        if st == "done":
            return row
        if st in ("failed", "cancelled"):
            raise RuntimeError(row.get("erro_mensagem") or st)
        time.sleep(interval)
    raise TimeoutError(f"Timeout {timeout}s aguardando {uuid}")


def _run_api(payload_dict: dict[str, Any], api_base: str) -> dict[str, Any]:
    import httpx

    url = api_base.rstrip("/") + "/api/relatorios"
    r = httpx.post(url, json=payload_dict, timeout=120)
    r.raise_for_status()
    return r.json()


def _append_run_log(entry: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    path = RUNS_DIR / f"runs_{day}.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Market Atlas — disparo de ondas")
    parser.add_argument("--wave", choices=("red", "transition", "blue"), help="Filtrar onda")
    parser.add_argument("--id", dest="scenario_id", help="Um cenário do CSV (id)")
    parser.add_argument(
        "--mode",
        choices=("api", "local", "stub"),
        default=os.getenv("MARKET_WAVE_MODE", "api"),
    )
    parser.add_argument("--api-base", default=os.getenv("VITE_API_BASE", "https://gymsite-api.vectracargo.com.br"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--delay", type=int, default=0, help="Segundos entre cenários (api/local)")
    parser.add_argument("--poll", type=int, default=30)
    parser.add_argument("--timeout", type=int, default=2100)
    parser.add_argument("--research", choices=("auto", "gemini", "kimi"), default="auto")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-city-wide", action="store_true")
    args = parser.parse_args()

    if not args.wave and not args.scenario_id:
        parser.error("Informe --wave ou --id")

    scenarios = _load_scenarios(
        wave=args.wave,
        scenario_id=args.scenario_id,
        limit=args.limit,
        allow_city_wide=args.allow_city_wide,
    )
    if not scenarios:
        print("Nenhum cenário encontrado.", file=sys.stderr)
        return 1

    print(f"Cenários: {len(scenarios)} | modo={args.mode}")
    if args.dry_run:
        for row in scenarios:
            inp = _input_from_scenario(row)
            print(
                f"  - {row['id']}: {inp['bairro']}/{inp['cidade']}-{inp.get('uf')} "
                f"[{row['wave']}] golden={row.get('golden_anchor') or '—'}"
            )
        return 0

    from api import NovoRelatorioInput
    from tools.postgrest_sb import (
        create_relatorio_stub_postgrest,
        patch_relatorio_atlas_meta,
    )

    results: list[dict[str, Any]] = []
    for i, row in enumerate(scenarios):
        sid = row["id"]
        inp_raw = _input_from_scenario(row)
        print(f"\n[{i + 1}/{len(scenarios)}] {sid}")
        print(f"  {inp_raw['bairro']} / {inp_raw['cidade']}-{inp_raw.get('uf')}")

        payload = NovoRelatorioInput(
            cidade=inp_raw["cidade"],
            bairro=inp_raw["bairro"],
            uf=inp_raw.get("uf") or "CE",
            area_m2_min=int(inp_raw.get("area_m2_min") or 800),
            area_m2_max=int(inp_raw.get("area_m2_max") or 1500),
            tamanho_preset=inp_raw.get("tamanho_preset") or "m",
            publico_alvo=inp_raw.get("publico_alvo") or "25-40",
            genero_alvo=inp_raw.get("genero_alvo") or "misto",
            tipo_negocio=inp_raw.get("tipo_negocio") or "academia",
            estacionamento_obrigatorio=bool(inp_raw.get("estacionamento_obrigatorio", True)),
            a0_research_provider=args.research,
        )
        payload_dict = payload.model_dump()

        relatorio_id: str
        status = "queued"

        try:
            if args.mode == "api":
                stub = _run_api(payload_dict, args.api_base)
                relatorio_id = stub["id"]
                print(f"  enfileirado via API: {relatorio_id}")
                if args.poll > 0:
                    _poll_done(relatorio_id, interval=args.poll, timeout=args.timeout)
                    status = "done"
            else:
                relatorio_id, _ = create_relatorio_stub_postgrest(payload)
                patch_relatorio_atlas_meta(
                    relatorio_id,
                    market_wave=row["wave"],
                    market_tier_qwen=row.get("tier_qwen"),
                )
                print(f"  stub: {relatorio_id}")
                if args.mode == "local":
                    import asyncio

                    from api import _run_pipeline_async

                    t0 = time.time()
                    asyncio.run(_run_pipeline_async(relatorio_id, payload))
                    wall = int(time.time() - t0)
                    print(f"  pipeline local {wall}s")
                    _poll_done(
                        relatorio_id,
                        interval=args.poll,
                        timeout=max(60, args.timeout - wall),
                    )
                    status = "done"
                else:
                    status = "stub"

            if args.mode == "api":
                patch_relatorio_atlas_meta(
                    relatorio_id,
                    market_wave=row["wave"],
                    market_tier_qwen=row.get("tier_qwen"),
                )

            entry = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "scenario_id": sid,
                "wave": row["wave"],
                "relatorio_id": relatorio_id,
                "status": status,
            }
            results.append(entry)
            _append_run_log(entry)
            print(f"  OK → {relatorio_id}")

        except Exception as e:
            print(f"  ERRO: {e}", file=sys.stderr)
            results.append(
                {
                    "scenario_id": sid,
                    "wave": row["wave"],
                    "status": "error",
                    "error": str(e),
                }
            )

        if args.delay > 0 and i < len(scenarios) - 1:
            time.sleep(args.delay)

    ok = sum(1 for r in results if r.get("status") in ("done", "stub", "queued"))
    print(f"\nResumo: {ok}/{len(scenarios)} OK | log em {RUNS_DIR}")
    return 0 if ok == len(scenarios) else 2


if __name__ == "__main__":
    raise SystemExit(main())
