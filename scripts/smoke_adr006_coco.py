#!/usr/bin/env python3
"""Smoke ADR-006: POST Cocó + poll status + Redis snapshot + WS progress."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

API = (os.getenv("SMOKE_API_BASE") or "https://api.getgymsite.com.br").rstrip("/")

PAYLOAD = {
    "cidade": "Fortaleza",
    "uf": "CE",
    "bairro": "Cocó",
    "area_m2_min": 800,
    "area_m2_max": 1200,
    "tamanho_preset": "m",
    "publico_alvo": "25-40",
    "genero_alvo": "misto",
    "tipo_negocio": "academia",
    "estacionamento_obrigatorio": True,
}


def _post() -> str:
    import httpx

    r = httpx.post(f"{API}/api/relatorios", json=PAYLOAD, timeout=60)
    r.raise_for_status()
    data = r.json()
    rid = data["id"]
    print(f"POST ok id={rid} status={data.get('status')}", flush=True)
    return rid


def _poll(rid: str) -> dict:
    import httpx

    r = httpx.get(f"{API}/api/relatorios/{rid}/status", timeout=30)
    r.raise_for_status()
    return r.json()


def _pipeline_status(rid: str) -> dict:
    import httpx

    r = httpx.get(f"{API}/api/pipeline/status", params={"relatorio_id": rid}, timeout=30)
    r.raise_for_status()
    return r.json()


async def _ws_listen(rid: str, stop: asyncio.Event, events: list) -> None:
    try:
        import websockets
    except ImportError:
        print("websockets não instalado — só poll HTTP", flush=True)
        return

    url = API.replace("https://", "wss://").replace("http://", "ws://")
    url = f"{url}/ws/pipeline?relatorio_id={rid}"
    try:
        async with websockets.connect(url, open_timeout=15, ping_interval=20) as ws:
            print(f"WS connected {url}", flush=True)
            while not stop.is_set():
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                except asyncio.TimeoutError:
                    continue
                msg = json.loads(raw)
                events.append({"t": time.time(), "msg": msg})
                mtype = msg.get("type")
                if mtype == "agent.progress":
                    d = msg.get("data") or {}
                    print(
                        f"  WS progress {d.get('agent_id')} {d.get('status')} "
                        f"lat_ms={d.get('latency_ms')}",
                        flush=True,
                    )
                elif mtype == "degraded":
                    print(f"  WS DEGRADED {msg.get('error')}", flush=True)
                elif mtype == "init":
                    print(
                        f"  WS init source={msg.get('source')} agents={list((msg.get('agents') or {}).keys())}",
                        flush=True,
                    )
    except Exception as e:
        print(f"WS error: {type(e).__name__}: {e}", flush=True)


async def main() -> int:
    t0 = time.time()
    rid = await asyncio.to_thread(_post)
    stop = asyncio.Event()
    events: list = []
    ws_task = asyncio.create_task(_ws_listen(rid, stop, events))

    last_etapa = None
    timeout = int(os.getenv("SMOKE_TIMEOUT_SEC", "2400"))
    while time.time() - t0 < timeout:
        row = await asyncio.to_thread(_poll, rid)
        st = row.get("status")
        etapa = row.get("etapa_atual")
        etapas = row.get("etapas_concluidas") or []
        wall = round(time.time() - t0, 1)
        if etapa != last_etapa:
            print(
                f"[{wall:>7}s] status={st} etapa={etapa} concluidas={len(etapas)}",
                flush=True,
            )
            last_etapa = etapa
            try:
                snap = await asyncio.to_thread(_pipeline_status, rid)
                agents = snap.get("agents") or {}
                if agents:
                    print(f"         redis_snap={list(agents.keys())} source={snap.get('source')}", flush=True)
            except Exception as e:
                print(f"         pipeline/status fail: {e}", flush=True)

        if st in ("done", "failed", "cancelled"):
            stop.set()
            await asyncio.sleep(1)
            wall = round(time.time() - t0, 1)
            print("==== RESULT ====", flush=True)
            print(json.dumps({
                "relatorio_id": rid,
                "status": st,
                "wall_s": wall,
                "tempo_execucao_segundos": row.get("tempo_execucao_segundos"),
                "erro": row.get("erro_mensagem"),
                "etapas_concluidas": etapas,
                "ws_events": len(events),
                "ws_progress": sum(
                    1 for e in events if (e.get("msg") or {}).get("type") == "agent.progress"
                ),
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False, indent=2), flush=True)
            ws_task.cancel()
            return 0 if st == "done" else 1

        await asyncio.sleep(15)

    stop.set()
    print("TIMEOUT", flush=True)
    ws_task.cancel()
    return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
