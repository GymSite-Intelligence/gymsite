"""Smoke test do MCP local (JSON-RPC em http://127.0.0.1:8001/mcp)."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

MCP_URL = "http://127.0.0.1:8001/mcp"
MCP_HEALTH_URL = "http://127.0.0.1:8001/health"
API_HEALTH_URL = "http://127.0.0.1:8000/health"


def _post(payload: dict, timeout: float = 15.0) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        MCP_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"raw": raw}
        return {"error": parsed, "http_status": exc.code}


def _get(url: str, timeout: float = 5.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    print("=== GymSite MCP smoke test ===\n")

    try:
        mcp_health = _get(MCP_HEALTH_URL)
        print(f"mcp health: {mcp_health}")
    except Exception as exc:
        print(f"FAIL mcp health: {exc}")
        print("Suba o MCP: .venv\\Scripts\\python.exe mcp_server.py")
        return 1

    try:
        api_health = _get(API_HEALTH_URL)
        print(f"api health: {api_health}")
    except Exception as exc:
        print(f"FAIL api health: {exc}")
        print("Suba a API: .venv\\Scripts\\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8000")
        return 1

    init = _post(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test_mcp_local", "version": "1.0"},
            },
        }
    )
    print(f"initialize: ok ({init['result']['serverInfo']})")

    tools_resp = _post({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    tools = tools_resp["result"]["tools"]
    names = [t["name"] for t in tools]
    print(f"\ntools/list: {len(names)} tools")
    for name in names:
        print(f"  - {name}")

    print("\n--- call gymsite_geocodificar(endereco='Curitiba, PR') ---")
    geo = _post(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "gymsite_geocodificar",
                "arguments": {"endereco": "Curitiba, PR"},
            },
        }
    )
    if "error" in geo:
        print(f"FAIL geocode: {json.dumps(geo['error'], ensure_ascii=False, indent=2)}")
        return 1
    text = geo["result"]["content"][0]["text"]
    print(text[:500])

    print("\n--- call gymsite_listar_relatorios(limit=3) ---")
    rel = _post(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "gymsite_listar_relatorios",
                "arguments": {"limit": 3},
            },
        },
        timeout=30.0,
    )
    if "error" in rel:
        print(f"FAIL relatorios: {rel['error']}")
        return 1
    text = rel["result"]["content"][0]["text"]
    print(text[:800])

    print("\nOK — MCP respondendo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
