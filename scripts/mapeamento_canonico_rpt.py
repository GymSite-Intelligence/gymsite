#!/usr/bin/env python3
"""
Mapeamento canônico: arquivo metrics/relatorios/rpt_<ts>.json ↔ UUID Supabase.

O JSON local usa `id` = `rpt_<unix_ts>` (adk_run_id).
O viewer/API usam `relatorios.id` (UUID).

Uso:
  python scripts/mapeamento_canonico_rpt.py
  python scripts/mapeamento_canonico_rpt.py rpt_1779819017 rpt_1779835541
  python scripts/mapeamento_canonico_rpt.py --dir metrics/relatorios
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

DEFAULT_RPTS = [
    "rpt_1779819017",
    "rpt_1779835541",
    "rpt_1779992079",
    "rpt_1780058853",
    "rpt_1780081675",
]


def _adk_id_from_path(path: Path) -> str:
    return path.stem if path.suffix == ".json" else path.name


def _load_local(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"WARN: não leu {path}: {exc}", file=sys.stderr)
        return None


def _fetch_supabase_by_adk(adk_ids: list[str]) -> dict[str, dict]:
    import os

    import httpx

    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise SystemExit(
            "SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY ausentes — use .env na raiz."
        )

    out: dict[str, dict] = {}
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }
    # PostgREST: in.(a,b,c)
    for i in range(0, len(adk_ids), 20):
        chunk = adk_ids[i : i + 20]
        quoted = ",".join(f'"{a}"' for a in chunk)
        req_url = (
            f"{url}/rest/v1/relatorios"
            f"?select=id,adk_run_id,status,data_execucao,created_at"
            f"&adk_run_id=in.({quoted})"
        )
        r = httpx.get(req_url, headers=headers, timeout=30)
        r.raise_for_status()
        for row in r.json() or []:
            aid = row.get("adk_run_id")
            if aid:
                out[str(aid)] = row
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Mapeia rpt_*.json → UUID Supabase")
    parser.add_argument(
        "rpts",
        nargs="*",
        help="adk_run_id ou nome de arquivo (default: lista fixa de 5 runs)",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=ROOT / "metrics" / "relatorios",
        help="Pasta dos JSON canônicos",
    )
    args = parser.parse_args()

    rel_dir: Path = args.dir
    adk_ids: list[str] = []
    if args.rpts:
        adk_ids = [_adk_id_from_path(Path(r)) for r in args.rpts]
    elif rel_dir.is_dir():
        adk_ids = sorted(_adk_id_from_path(p) for p in rel_dir.glob("rpt_*.json"))
    if not adk_ids:
        adk_ids = list(DEFAULT_RPTS)

    rows: list[dict] = []
    for adk in adk_ids:
        path = rel_dir / f"{adk}.json"
        data = _load_local(path)
        inp = (data or {}).get("input_canonico") or {}
        out = (data or {}).get("output_consolidado") or {}
        rows.append(
            {
                "adk_run_id": adk,
                "arquivo": str(path) if path.is_file() else "(ausente)",
                "cidade": inp.get("cidade", "?"),
                "bairro": inp.get("bairro", "?"),
                "veredito": out.get("veredito", "?"),
                "score_top1": out.get("score_top1_candidato"),
            }
        )

    try:
        sb_map = _fetch_supabase_by_adk([r["adk_run_id"] for r in rows])
    except SystemExit as e:
        print(e, file=sys.stderr)
        sb_map = {}

    hdr = (
        f"{'adk_run_id':<22} | {'uuid':<38} | {'status':<8} | "
        f"{'cidade':<14} | {'bairro':<14} | {'veredito':<22} | arquivo"
    )
    print(hdr)
    print("-" * len(hdr))

    for r in rows:
        adk = r["adk_run_id"]
        sb = sb_map.get(adk) or {}
        uuid = sb.get("id") or "—"
        status = sb.get("status") or "—"
        cidade = str(r["cidade"])[:14]
        bairro = str(r["bairro"])[:14]
        veredito = str(r["veredito"])[:22]
        arquivo = "ok" if r["arquivo"] != "(ausente)" else "MISSING"
        print(
            f"{adk:<22} | {uuid:<38} | {status:<8} | {cidade:<14} | "
            f"{bairro:<14} | {veredito:<22} | {arquivo}"
        )

    print()
    print("URLs viewer (quando uuid conhecido):")
    for r in rows:
        adk = r["adk_run_id"]
        uuid = (sb_map.get(adk) or {}).get("id")
        if uuid:
            print(f"  {adk} -> https://gymsite.vectracargo.com.br/relatorios/{uuid}")
        else:
            print(f"  {adk} -> (sem linha em relatorios.adk_run_id)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
