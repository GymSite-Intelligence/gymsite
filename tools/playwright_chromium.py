"""Playwright launch using system Chromium (Docker/CI — no ms-playwright browser bundle)."""
from __future__ import annotations

import os
from typing import Any


def _default_args() -> list[str]:
    args = ["--disable-blink-features=AutomationControlled"]
    if os.path.exists("/.dockerenv"):
        args.extend(["--no-sandbox", "--disable-dev-shm-usage"])
    return args


def chromium_launch_kwargs(**overrides: Any) -> dict[str, Any]:
    opts: dict[str, Any] = {"headless": True, "args": _default_args()}
    exe = (os.getenv("CHROMIUM_EXECUTABLE_PATH") or "").strip()
    if exe and os.path.isfile(exe):
        opts["executable_path"] = exe
    extra_args = overrides.pop("args", None)
    if extra_args is not None:
        opts["args"] = _default_args() + list(extra_args)
    opts.update(overrides)
    return opts
