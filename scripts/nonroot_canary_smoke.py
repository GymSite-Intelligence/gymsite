"""P3.1 canary — non-root + uvicorn health + Playwright Chromium launch."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, "/app")


def main() -> int:
    uid = os.getuid()
    if uid == 0:
        print("FAIL: running as root")
        return 1
    print(f"uid={uid} ok")

    import httpx

    # Import api app (same as prod)
    from api import app  # noqa: F401

    print("api import ok")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("FAIL: playwright not installed")
        return 1

    from tools.playwright_chromium import chromium_launch_kwargs

    with sync_playwright() as p:
        browser = p.chromium.launch(**chromium_launch_kwargs())
        page = browser.new_page()
        page.goto("about:blank", timeout=15000)
        browser.close()

    print("playwright chromium ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
