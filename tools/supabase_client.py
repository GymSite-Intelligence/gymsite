"""Load supabase-py create_client without repo supabase/ (CLI) shadowing."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any, Callable

_REPO_ROOT = Path(__file__).resolve().parent.parent


def load_create_client() -> Callable[..., Any]:
    root = _REPO_ROOT.resolve()
    saved_path = list(sys.path)
    to_clear = [k for k in sys.modules if k == "supabase" or k.startswith("supabase.")]
    try:
        for k in to_clear:
            del sys.modules[k]
        sys.path = [p for p in sys.path if p and Path(p).resolve() != root]
        mod = importlib.import_module("supabase")
        cc = getattr(mod, "create_client", None)
        if cc is None:
            raise ImportError(
                "cannot import create_client from supabase; pip install supabase>=2.0.0; repo supabase/ is CLI config"
            )
        return cc
    finally:
        sys.path[:] = saved_path

