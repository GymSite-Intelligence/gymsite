#!/usr/bin/env python3
"""
Layer 3 - marca relatorios running/queued orfaos como failed (sem relatorio_outputs).

Mesma logica de api._recover_stale_running_reports (PIPELINE_ORPHAN_MINUTES,
PIPELINE_STALE_HOURS, PIPELINE_MAX_WALL_SEC), sem importar api.py.

Uso:
  python scripts/cleanup_orphan_reports.py
  python scripts/cleanup_orphan_reports.py --dry-run
  python scripts/cleanup_orphan_reports.py --relatorio-id <uuid>
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

_UUID_RE = (
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)

_STALE_PIPELINE_HOURS = int(os.getenv("PIPELINE_STALE_HOURS", "6"))
_PIPELINE_ORPHAN_MINUTES = int(os.getenv("PIPELINE_ORPHAN_MINUTES", "35"))
_PIPELINE_WALL_BUFFER_MIN = int(os.getenv("PIPELINE_WALL_BUFFER_MIN", "5"))
_PIPELINE_MAX_WALL_SEC = int(os.getenv("PIPELINE_MAX_WALL_SEC", "1800"))

_STALE_MSG = (
    "Pipeline interrompido (restart do servidor ou timeout). "
    "Use Gerar novamente para reprocessar."
)


def _sb_headers() -> tuple[str, dict[str, str]]:
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise SystemExit("SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY ausentes no .env")
    return url, {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _pipeline_stale_cutoff() -> datetime:
    wall_hours = _PIPELINE_MAX_WALL_SEC / 3600.0 + _PIPELINE_WALL_BUFFER_MIN / 60.0
    hours_floor = max(float(_STALE_PIPELINE_HOURS), wall_hours)
    age = min(
        timedelta(hours=hours_floor),
        timedelta(minutes=_PIPELINE_ORPHAN_MINUTES),
    )
    return datetime.now(timezone.utc) - age


def _resolve_relatorio_uuid(base: str, headers: dict[str, str], relatorio_id: str) -> str:
    if re.match(_UUID_RE, relatorio_id, re.I):
        return relatorio_id
    if relatorio_id.startswith("rpt_"):
        import httpx

        r = httpx.get(
            f"{base}/rest/v1/relatorios",
            headers=headers,
            params={
                "adk_run_id": f"eq.{relatorio_id}",
                "select": "id",
                "limit": "1",
            },
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and data:
            return str(data[0]["id"])
    return relatorio_id


def _fetch_stale_candidates(
    base: str,
    headers: dict[str, str],
    *,
    relatorio_id: str | None,
) -> list[dict]:
    import httpx

    cutoff = _pipeline_stale_cutoff().isoformat()
    params: dict[str, str] = {
        "select": "id,status,updated_at",
        "status": "in.(running,queued)",
        "updated_at": f"lt.{cutoff}",
    }
    if relatorio_id:
        rid = _resolve_relatorio_uuid(base, headers, relatorio_id)
        params["id"] = f"eq.{rid}"

    r = httpx.get(
        f"{base}/rest/v1/relatorios",
        headers=headers,
        params=params,
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else []


def _has_output(base: str, headers: dict[str, str], relatorio_id: str) -> bool:
    import httpx

    r = httpx.get(
        f"{base}/rest/v1/relatorio_outputs",
        headers=headers,
        params={
            "relatorio_id": f"eq.{relatorio_id}",
            "select": "relatorio_id",
            "limit": "1",
        },
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    return bool(isinstance(data, list) and data)


def _mark_failed(base: str, headers: dict[str, str], relatorio_id: str) -> None:
    import httpx

    patch_headers = {**headers, "Prefer": "return=minimal"}
    r = httpx.patch(
        f"{base}/rest/v1/relatorios",
        headers=patch_headers,
        params={"id": f"eq.{relatorio_id}"},
        json={"status": "failed", "erro_mensagem": _STALE_MSG},
        timeout=60,
    )
    r.raise_for_status()


def recover_stale_orphans(
    *,
    dry_run: bool,
    relatorio_id: str | None,
) -> int:
    base, headers = _sb_headers()
    try:
        rows = _fetch_stale_candidates(base, headers, relatorio_id=relatorio_id)
        recovered = 0
        for row in rows:
            rid = str(row["id"])
            if _has_output(base, headers, rid):
                continue
            if dry_run:
                recovered += 1
                continue
            _mark_failed(base, headers, rid)
            print(f"orfao recuperado: {rid} (era {row.get('status')})", file=sys.stderr)
            recovered += 1
        return recovered
    except Exception as e:
        print(f"recover_stale_orphans: {e}", file=sys.stderr)
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Recupera relatorios pipeline orfaos")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="So conta candidatos; nao atualiza o banco",
    )
    parser.add_argument(
        "--relatorio-id",
        default=None,
        help="Limita a um relatorio (UUID ou adk_run_id rpt_*)",
    )
    args = parser.parse_args()

    n = recover_stale_orphans(dry_run=args.dry_run, relatorio_id=args.relatorio_id)
    if args.dry_run:
        print(f"Candidatos orfaos (running/queued, sem output): {n}")
    else:
        print(f"Recuperados {n} relatorio(s) orfao(s) -> status=failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
