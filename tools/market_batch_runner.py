"""Invocação programática do batch semanal (cron Supabase → Cloud Run)."""
from __future__ import annotations

import logging
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("gymsite.market_batch")

ROOT = Path(__file__).resolve().parent.parent
_LOCK = threading.Lock()


@dataclass
class BatchRunState:
    running: bool = False
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None
    error: str | None = None
    args: list[str] = field(default_factory=list)


_STATE = BatchRunState()


def batch_state() -> dict[str, Any]:
    s = _STATE
    return {
        "running": s.running,
        "started_at": s.started_at,
        "finished_at": s.finished_at,
        "exit_code": s.exit_code,
        "error": s.error,
        "args": list(s.args),
    }


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_weekly_market_batch(
    *,
    skip_cvm: bool = False,
    skip_sinapi: bool = False,
    skip_benchmarks: bool = False,
    skip_bundles: bool = False,
    skip_enrichment: bool = True,
    only_cvm: bool = False,
) -> int:
    """Executa scripts/batch/run_weekly_market_batch.py (bloqueante)."""
    script = ROOT / "scripts" / "batch" / "run_weekly_market_batch.py"
    cmd = [sys.executable, str(script)]
    if skip_cvm:
        cmd.append("--skip-cvm")
    if skip_sinapi:
        cmd.append("--skip-sinapi")
    if skip_benchmarks:
        cmd.append("--skip-benchmarks")
    if skip_bundles:
        cmd.append("--skip-bundles")
    if skip_enrichment:
        cmd.append("--skip-enrichment")
    if only_cvm:
        cmd.append("--only-cvm")

    logger.info("weekly market batch start: %s", " ".join(cmd))
    rc = subprocess.call(cmd, cwd=str(ROOT))
    logger.info("weekly market batch done exit=%s", rc)
    return rc


def start_weekly_market_batch_async(
    *,
    skip_enrichment: bool = True,
    only_cvm: bool = False,
) -> dict[str, Any]:
    """Dispara batch em thread daemon. Retorna imediato (cron HTTP 202)."""
    if _STATE.running:
        return {"status": "already_running", **batch_state()}

    if not _LOCK.acquire(blocking=False):
        return {"status": "already_running", **batch_state()}

    args_label = ["--skip-enrichment"]
    if only_cvm:
        args_label.append("--only-cvm")

    _STATE.running = True
    _STATE.started_at = _iso_now()
    _STATE.finished_at = None
    _STATE.exit_code = None
    _STATE.error = None
    _STATE.args = args_label

    def _worker() -> None:
        try:
            rc = run_weekly_market_batch(
                skip_enrichment=skip_enrichment,
                only_cvm=only_cvm,
            )
            _STATE.exit_code = rc
            if rc != 0:
                _STATE.error = f"exit_code={rc}"
        except Exception as exc:  # noqa: BLE001
            logger.exception("weekly market batch thread failed")
            _STATE.exit_code = 1
            _STATE.error = f"{type(exc).__name__}: {exc}"
        finally:
            _STATE.finished_at = _iso_now()
            _STATE.running = False
            _LOCK.release()

    threading.Thread(target=_worker, name="weekly-market-batch", daemon=True).start()
    return {"status": "started", **batch_state()}
