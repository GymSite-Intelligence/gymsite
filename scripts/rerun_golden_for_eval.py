#!/usr/bin/env python3
"""
Re-roda pipeline A0-A9 para um golden case e re-extrai snapshots.

Stub/polling via httpx (tools/postgrest_sb.py) para nao depender de supabase-py
quando a pasta supabase/ (CLI) na raiz sombreia o pacote Python.
Pipeline: pip install -r requirements.txt no .venv. Alternativa:
  docker compose exec api python scripts/rerun_golden_for_eval.py <case>

Uso:
  python scripts/rerun_golden_for_eval.py fortaleza_parangaba_20260528
  python scripts/rerun_golden_for_eval.py --case niteroi_camboinhas_20260513 --poll 30
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def _poll_done(uuid: str, *, interval: int, timeout: int) -> str:
    from tools.postgrest_sb import fetch_relatorio_status

    t0 = time.time()
    while time.time() - t0 < timeout:
        row = fetch_relatorio_status(uuid)
        if not row:
            raise RuntimeError(f"Relatorio {uuid} nao encontrado")
        st = row.get("status")
        elapsed = row.get("tempo_execucao_segundos")
        print(f"  status={st} tempo={elapsed}s", flush=True)
        if st == "done":
            return "done"
        if st in ("failed", "cancelled"):
            msg = row.get("erro_mensagem") or st
            raise RuntimeError(f"Pipeline {st}: {msg}")
        time.sleep(interval)
    raise TimeoutError(f"Timeout apos {timeout}s aguardando {uuid}")


def _has_posicionamento(uuid: str) -> bool:
    from tools.postgrest_sb import fetch_posicionamento_flag

    try:
        return fetch_posicionamento_flag(uuid)
    except Exception as e:
        print(f"AVISO: nao foi possivel ler posicionamento_estrategico: {e}", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Rerun pipeline + re-extract golden")
    parser.add_argument(
        "case",
        nargs="?",
        help="Nome da pasta em eval/golden_dataset (ex: fortaleza_parangaba_20260528)",
    )
    parser.add_argument("--case", dest="case_flag", help="Alias para o case id")
    parser.add_argument("--dataset", default="eval/golden_dataset")
    parser.add_argument("--poll", type=int, default=30, help="Intervalo de polling (s)")
    parser.add_argument(
        "--timeout",
        type=int,
        default=2100,
        help="Timeout total de espera (s); default 35 min",
    )
    parser.add_argument(
        "--research",
        choices=("auto", "gemini", "kimi"),
        default="auto",
    )
    parser.add_argument("--dry-run", action="store_true", help="So imprime payload, nao roda")
    args = parser.parse_args()

    case_id = args.case_flag or args.case
    if not case_id:
        parser.error("Informe o case (ex: fortaleza_parangaba_20260528)")

    case_dir = ROOT / args.dataset / case_id
    input_path = case_dir / "input.json"
    if not input_path.is_file():
        raise SystemExit(f"input.json nao encontrado: {input_path}")

    inp = json.loads(input_path.read_text(encoding="utf-8"))
    print(f"Case: {case_id}")
    print(f"  {inp.get('bairro')} / {inp.get('cidade')}-{inp.get('uf')}")

    if args.dry_run:
        print(json.dumps(inp, indent=2, ensure_ascii=False))
        return 0

    import asyncio

    from api import NovoRelatorioInput, _run_pipeline_async
    from tools.postgrest_sb import create_relatorio_stub_postgrest

    payload = NovoRelatorioInput(
        cidade=inp["cidade"],
        bairro=inp["bairro"],
        uf=inp.get("uf") or "CE",
        area_m2_min=int(inp.get("area_m2_min") or 800),
        area_m2_max=int(inp.get("area_m2_max") or 1500),
        tamanho_preset=inp.get("tamanho_preset") or "m",
        publico_alvo=inp.get("publico_alvo") or "25-40",
        genero_alvo=inp.get("genero_alvo") or "misto",
        tipo_negocio=inp.get("tipo_negocio") or "academia",
        estacionamento_obrigatorio=bool(inp.get("estacionamento_obrigatorio", True)),
        a0_research_provider=args.research,
    )

    relatorio_id, _ = create_relatorio_stub_postgrest(payload)
    print(f"Novo relatorio: {relatorio_id}")
    print("Iniciando pipeline (A0-A9)...", flush=True)
    t0 = time.time()
    asyncio.run(_run_pipeline_async(relatorio_id, payload))
    wall = int(time.time() - t0)
    print(f"Pipeline retornou em {wall}s wall-clock local")

    _poll_done(relatorio_id, interval=args.poll, timeout=max(60, args.timeout - wall))

    if not _has_posicionamento(relatorio_id):
        print(
            "AVISO: posicionamento_estrategico ausente no Supabase - "
            "confira migration 20260530 e logs do A9.",
            file=sys.stderr,
        )

    from scripts.extract_golden_case import extract_golden_case

    print(f"Re-extraindo para {case_dir}.")
    extract_golden_case(
        relatorio_id,
        ROOT / args.dataset,
        target_case_dir=case_dir,
    )

    full = json.loads((case_dir / "full_report.json").read_text(encoding="utf-8"))
    oc = full.get("output_consolidado") or {}
    has_pos = isinstance(oc.get("posicionamento_estrategico"), dict) and bool(
        oc.get("posicionamento_estrategico")
    )
    print(f"OK full_report atualizado | A9 no snapshot: {'sim' if has_pos else 'nao'}")
    print(f"UUID novo (anotar em notes): {relatorio_id}")
    return 0 if has_pos else 2


if __name__ == "__main__":
    raise SystemExit(main())

