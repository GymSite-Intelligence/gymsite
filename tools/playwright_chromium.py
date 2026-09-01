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
    if exe:
        # Falha alto: com PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 não há bundle ms-playwright,
        # então path configurado mas ausente daria erro opaco no launch — melhor barrar aqui.
        if not os.path.isfile(exe):
            raise FileNotFoundError(
                f"CHROMIUM_EXECUTABLE_PATH={exe!r} não é um arquivo — "
                "sem browser bundle o Playwright falharia no launch."
            )
        opts["executable_path"] = exe
    extra_args = overrides.pop("args", None)
    if extra_args is not None:
        opts["args"] = _default_args() + list(extra_args)
    opts.update(overrides)
    return opts
