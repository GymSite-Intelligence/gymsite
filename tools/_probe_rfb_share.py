from __future__ import annotations

import re
import sys

import httpx


def main(url: str) -> int:
    r = httpx.get(url, timeout=30.0, follow_redirects=True)
    print("status:", r.status_code)
    print("content-type:", r.headers.get("content-type"))
    html = r.text
    print("html_len:", len(html))

    # Heurísticas: Nextcloud shares costumam expor endpoints /download e /public.php/webdav
    candidates = set()
    for m in re.finditer(r"""(?i)(https?://[^\s"'<>]+)""", html):
        s = m.group(1)
        if "arquivos.receitafederal.gov.br" in s and (
            "/download" in s or "/index.php/" in s or "webdav" in s
        ):
            candidates.add(s)

    for m in re.finditer(r"""/index\.php/[^\s"'<>]+""", html):
        s = "https://arquivos.receitafederal.gov.br" + m.group(0)
        if "/download" in s or "/s/" in s or "webdav" in s:
            candidates.add(s)

    print("candidates:", len(candidates))
    for s in sorted(candidates)[:80]:
        print("-", s)

    # Dump a few markers
    for needle in ["download", "webdav", "share", "requesttoken", "public.php"]:
        print(f"has_{needle}:", needle in html.lower())

    return 0


if __name__ == "__main__":
    u = sys.argv[1] if len(sys.argv) > 1 else ""
    if not u:
        print("usage: python tools/_probe_rfb_share.py <url>")
        raise SystemExit(2)
    raise SystemExit(main(u))

