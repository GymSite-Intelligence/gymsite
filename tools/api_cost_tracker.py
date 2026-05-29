# tools/api_cost_tracker.py
import csv
import os
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional
from contextvars import ContextVar

# ContextVar to track the current report ID across async/thread boundaries
current_relatorio_id: ContextVar[Optional[str]] = ContextVar("current_relatorio_id", default=None)

METRICS_DIR = Path(__file__).resolve().parent.parent / "metrics"
CSV_PATH = METRICS_DIR / "api_calls_pipeline.csv"
CSV_HEADER = [
    "run_id",
    "timestamp",
    "tool_name",
    "api_sku",
    "num_calls",
    "custo_brl",
]

_WRITE_LOCK = threading.Lock()

def _ensure_csv_header() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    with _WRITE_LOCK:
        if not CSV_PATH.exists():
            with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(CSV_HEADER)

def _get_run_id() -> str:
    try:
        from tools.token_telemetry import _get_run_id as get_token_run_id
        return get_token_run_id()
    except Exception:
        return "unknown"

def log_api_call_locally(tool_name: str, api_sku: str, num_calls: int, custo_brl: float) -> None:
    try:
        _ensure_csv_header()
        row = [
            _get_run_id(),
            datetime.now().isoformat(timespec="seconds"),
            tool_name,
            api_sku,
            num_calls,
            round(custo_brl, 6),
        ]
        with _WRITE_LOCK:
            with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(row)
    except Exception:
        pass

def log_api_call_to_db(relatorio_id: str, tool_name: str, api_sku: str, num_calls: int, custo_brl: float) -> None:
    try:
        from db.supabase_writer import _get_client
        client = _get_client()
        if client is None:
            return
        
        record = {
            "relatorio_id": relatorio_id,
            "agente": tool_name,
            "tool_name": tool_name,
            "api_sku": api_sku,
            "num_calls": num_calls,
            "custo_brl": round(custo_brl, 6),
        }
        client.table("relatorio_api_calls").insert(record).execute()
    except Exception:
        # Fail-safe to avoid crashing if table does not exist yet
        pass

@contextmanager
def track_api_call(tool_name: str, api_sku: str, num_calls: int = 1, relatorio_id: Optional[str] = None):
    # If relatorio_id is not passed, try to get it from ContextVar
    if not relatorio_id:
        relatorio_id = current_relatorio_id.get()
        
    yield
    
    try:
        from tools.pricing import compute_places_cost_brl
        custo_brl = compute_places_cost_brl(api_sku, num_calls)
        
        # Log locally
        log_api_call_locally(tool_name, api_sku, num_calls, custo_brl)
        
        # Log to DB
        if relatorio_id:
            log_api_call_to_db(relatorio_id, tool_name, api_sku, num_calls, custo_brl)
    except Exception:
        pass
