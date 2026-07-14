#!/usr/bin/env python3
"""CLI: choose Mermaid diagram type DETERMINISTICALLY and optionally render via Mermaid Chart MCP.

Examples:
  python scripts/batch/render_mermaid_diagram.py --texto "pipeline A0-A9 e decisões" --dry-run
  python scripts/batch/render_mermaid_diagram.py --intent sequencia --code sequence.mmd --render
  python scripts/batch/render_mermaid_diagram.py --dados '{"series":[1,2,3,4]}' --code chart.mmd --render

Render calls https://mcp.mermaid.ai/mcp tool validate_and_render_mermaid_diagram (public).
Saving into a Mermaid Chart account project needs MERMAID_CHART_TOKEN (not required for render).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.mermaid_diagram_router import escolher_diagrama, listar_regras  # noqa: E402


def _mcp_session() -> str:
    req = urllib.request.Request(
        "https://mcp.mermaid.ai/mcp",
        data=json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "gymsite-render-mermaid", "version": "1.0"},
                },
            }
        ).encode(),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        sid = resp.headers.get("Mcp-Session-Id") or resp.headers.get("mcp-session-id") or ""
    token = (os.getenv("MERMAID_CHART_TOKEN") or "").strip()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Mcp-Session-Id": sid,
    }
    if token:
        headers["Authorization"] = token if token.lower().startswith("bearer ") else f"Bearer {token}"
    urllib.request.urlopen(
        urllib.request.Request(
            "https://mcp.mermaid.ai/mcp",
            data=json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}).encode(),
            headers=headers,
            method="POST",
        ),
        timeout=30,
    ).read()
    return sid


def _parse_sse(body: str) -> dict:
    for line in body.splitlines():
        if line.startswith("data:"):
            return json.loads(line[5:].strip())
    return json.loads(body)


def render_mermaid(code: str, diagram_type: str, prompt: str) -> dict:
    sid = _mcp_session()
    token = (os.getenv("MERMAID_CHART_TOKEN") or "").strip()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Mcp-Session-Id": sid,
    }
    if token:
        headers["Authorization"] = token if token.lower().startswith("bearer ") else f"Bearer {token}"
    payload = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "validate_and_render_mermaid_diagram",
            "arguments": {
                "prompt": prompt or f"GymSite diagram ({diagram_type})",
                "mermaidCode": code,
                "diagramType": diagram_type.replace("-beta", ""),
                "clientName": "cursor",
                "useUrlShortener": True,
            },
        },
    }
    req = urllib.request.Request(
        "https://mcp.mermaid.ai/mcp",
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return _parse_sse(resp.read().decode())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--texto", default="", help="Free-text cue for keyword routing")
    ap.add_argument("--intent", default=None, help="Explicit intent (fluxo|sequencia|cronograma|...)")
    ap.add_argument("--dados", default=None, help="JSON dict with structural signals")
    ap.add_argument("--code", default=None, help="Path to .mmd file to render")
    ap.add_argument("--code-inline", default=None, help="Inline mermaid source")
    ap.add_argument("--render", action="store_true", help="Call Mermaid Chart MCP to render")
    ap.add_argument("--out-png", default=None, help="Write PNG bytes if render returns image")
    ap.add_argument("--list-rules", action="store_true", help="Print routing table and exit")
    ap.add_argument("--dry-run", action="store_true", help="Only print DiagramChoice JSON")
    args = ap.parse_args()

    if args.list_rules:
        print(json.dumps(listar_regras(), ensure_ascii=False, indent=2))
        return 0

    dados = json.loads(args.dados) if args.dados else None
    choice = escolher_diagrama(args.texto, intent=args.intent, dados=dados)
    print(json.dumps(choice.as_dict(), ensure_ascii=False, indent=2))

    if args.dry_run or not args.render:
        return 0

    if args.code:
        code = Path(args.code).read_text(encoding="utf-8")
    elif args.code_inline:
        code = args.code_inline
    else:
        print("error: --render requires --code or --code-inline", file=sys.stderr)
        return 2

    result = render_mermaid(code, choice.tipo, args.texto or choice.quando)
    content = (result.get("result") or {}).get("content") or []
    links = []
    import re

    for item in content:
        if item.get("type") == "text":
            text = item.get("text") or ""
            links.extend(re.findall(r"https://l\.mermaid\.ai/\w+", text))
            print(text[:1200])
        if item.get("type") == "image" and item.get("data") and args.out_png:
            import base64

            Path(args.out_png).write_bytes(base64.b64decode(item["data"]))
            print(json.dumps({"png": args.out_png, "bytes": Path(args.out_png).stat().st_size}))
    if links:
        print(json.dumps({"preview": links[0]}))
    if result.get("error") or (result.get("result") or {}).get("isError"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
