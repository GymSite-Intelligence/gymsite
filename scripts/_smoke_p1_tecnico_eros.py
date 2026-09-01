"""P1 smoke: Técnico Eros + Arquiteto/Eng fallback + Mercado (no receita)."""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
load_dotenv(ROOT / ".env.production", override=False)

BYPASS = (os.getenv("SITE_CHAT_BYPASS_TOKEN") or "").strip()
API = (
    os.getenv("SMOKE_API_BASE")
    or "https://gymsite-api.vectracargo.com.br"
).rstrip("/")
SB_URL = (os.getenv("SUPABASE_URL") or "").rstrip("/")
SB_ANON = (os.getenv("VITE_SUPABASE_ANON_KEY") or os.getenv("SUPABASE_ANON_KEY") or "").strip()
SB_SERVICE = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
ADMIN_EMAIL = (os.getenv("ADMIN_EMAILS") or "").split(",")[0].strip()

RE_RS = re.compile(r"(R\$\s*\d|\b\d{1,3}(?:\.\d{3})+,\d{2}\b|\bpre[cç]o\b.{0,20}\d)", re.I)


def http_json(method: str, url: str, body: dict | None = None, headers: dict | None = None, timeout: int = 60):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"raw": raw[:400]}
        return e.code, parsed


def poll_site(pid: str, timeout_s: int = 90) -> str:
    deadline = time.time() + timeout_s
    last = ""
    while time.time() < deadline:
        code, data = http_json("GET", f"{API}/api/site-agent/conversar/{pid}/mensagens")
        if code != 200:
            time.sleep(2)
            continue
        msgs = data.get("mensagens") or data.get("messages") or []
        if isinstance(data, dict) and not msgs:
            # some payloads nest under data
            msgs = data.get("items") or []
        texts = [
            (m.get("content") or "")
            for m in msgs
            if isinstance(m, dict) and m.get("role") == "assistant"
        ]
        if texts:
            last = texts[-1]
            if last.strip():
                return last
        time.sleep(2)
    return last


def smoke_site(label: str, agente: str, pergunta: str) -> dict:
    code, data = http_json(
        "POST",
        f"{API}/api/site-agent/conversar",
        {"mensagem": pergunta, "agente": agente, "dev_token": BYPASS},
        {"x-site-chat-token": BYPASS},
    )
    if code >= 400:
        return {"canal": "degustacao", "label": label, "ok": False, "detail": f"HTTP {code} {data}"}
    pid = data.get("projeto_id")
    if not pid:
        return {"canal": "degustacao", "label": label, "ok": False, "detail": f"sem projeto_id {data}"}
    texto = poll_site(pid)
    return {"canal": "degustacao", "label": label, "ok": bool(texto.strip()), "texto": texto, "projeto_id": pid}


def supabase_access_token() -> str | None:
    if not (SB_URL and SB_SERVICE and ADMIN_EMAIL):
        return None
    code, data = http_json(
        "POST",
        f"{SB_URL}/auth/v1/admin/generate_link",
        {"type": "magiclink", "email": ADMIN_EMAIL},
        {"Authorization": f"Bearer {SB_SERVICE}", "apikey": SB_SERVICE},
    )
    if code >= 400:
        print("consultor auth generate_link fail", code, str(data)[:200])
        return None
    props = data.get("properties") or {}
    hashed = props.get("hashed_token") or data.get("hashed_token")
    if not hashed:
        print("consultor auth sem hashed_token", str(data)[:300])
        return None
    code2, data2 = http_json(
        "POST",
        f"{SB_URL}/auth/v1/verify",
        {"type": "magiclink", "token_hash": hashed},
        {"apikey": SB_ANON or SB_SERVICE, "Authorization": f"Bearer {SB_ANON or SB_SERVICE}"},
    )
    if code2 >= 400:
        print("consultor auth verify fail", code2, str(data2)[:200])
        return None
    return (data2.get("access_token") or (data2.get("session") or {}).get("access_token"))


def poll_consultor(pid: str, token: str, timeout_s: int = 90) -> str:
    deadline = time.time() + timeout_s
    last = ""
    while time.time() < deadline:
        code, data = http_json(
            "GET",
            f"{API}/api/consultor/projetos/{pid}/mensagens",
            headers={"Authorization": f"Bearer {token}"},
        )
        if code != 200:
            time.sleep(2)
            continue
        msgs = data.get("mensagens") or data.get("messages") or data if isinstance(data, list) else []
        if isinstance(data, dict) and not msgs:
            msgs = data.get("items") or []
        texts = [
            (m.get("content") or "")
            for m in msgs
            if isinstance(m, dict) and m.get("role") == "assistant"
        ]
        if texts and texts[-1].strip():
            return texts[-1]
        time.sleep(2)
    return last


def smoke_consultor(label: str, agente: str, pergunta: str, token: str) -> dict:
    code, data = http_json(
        "POST",
        f"{API}/api/consultor/conversar",
        {"mensagem": pergunta, "agente": agente},
        {"Authorization": f"Bearer {token}"},
    )
    if code >= 400:
        return {"canal": "consultor", "label": label, "ok": False, "detail": f"HTTP {code} {data}"}
    pid = data.get("projeto_id") or (data.get("projeto") or {}).get("id")
    if not pid:
        return {"canal": "consultor", "label": label, "ok": False, "detail": f"sem projeto_id {data}"}
    texto = poll_consultor(pid, token)
    return {"canal": "consultor", "label": label, "ok": bool(texto.strip()), "texto": texto, "projeto_id": pid}


def verdict_tecnico_marca(texto: str) -> str:
    t = texto.lower()
    tem_marca = any(x in t for x in ("total health", "rrf", "totalhealth"))
    tem_rs = bool(RE_RS.search(texto)) or bool(re.search(r"r\$", t))
    if tem_marca and not tem_rs:
        return "ok"
    return "fail"


def verdict_preco(texto: str) -> str:
    t = texto.lower()
    sob = "sob consulta" in t or "consultar o fornecedor" in t or "consulta com o fornecedor" in t
    inventou = bool(re.search(r"r\$\s*\d", t)) or bool(re.search(r"\b\d[\d\.]*\s*(reais|mil)\b", t))
    if sob and not inventou:
        return "ok"
    return "fail"


def verdict_nao_receita(texto: str) -> str:
    t = texto.lower()
    if "57" in t and ("mil" in t or "000" in t or "receita" in t):
        return "fail"
    return "ok" if texto.strip() else "fail"


def main():
    if not BYPASS:
        print("FAIL: SITE_CHAT_BYPASS_TOKEN ausente")
        sys.exit(2)
    results = []
    results.append(smoke_site("tecnico_rrf", "responsavel_tecnico", "linha RRF Total Health"))
    results.append(smoke_site("tecnico_preco", "responsavel_tecnico", "quanto custa o kit"))
    results.append(smoke_site("arquiteto", "arquiteto", "carga de laje para academia NBR 6120"))
    results.append(smoke_site("engenheiro", "engenheiro_obra", "carga de laje para academia NBR 6120"))
    results.append(smoke_site("mercado", "mercado", "qual a metodologia de saturação do mercado fitness"))

    token = supabase_access_token()
    if token:
        results.append(smoke_consultor("tecnico_rrf", "responsavel_tecnico", "linha RRF Total Health", token))
        results.append(smoke_consultor("tecnico_preco", "responsavel_tecnico", "quanto custa o kit", token))
        results.append(smoke_consultor("arquiteto", "arquiteto", "carga de laje para academia NBR 6120", token))
        results.append(smoke_consultor("engenheiro", "engenheiro_obra", "carga de laje para academia NBR 6120", token))
        results.append(smoke_consultor("mercado", "mercado", "qual a metodologia de saturação do mercado fitness", token))
    else:
        results.append({"canal": "consultor", "label": "auth", "ok": False, "detail": "sem JWT"})

    print(json.dumps(results, ensure_ascii=False, indent=2)[:12000])
    print("\n=== VEREDITO ===")
    for r in results:
        texto = r.get("texto") or ""
        label = r["label"]
        canal = r["canal"]
        if not r.get("ok"):
            v = "fail"
        elif label == "tecnico_rrf":
            v = verdict_tecnico_marca(texto)
        elif label == "tecnico_preco":
            v = verdict_preco(texto)
        elif label in ("arquiteto", "engenheiro", "mercado"):
            v = verdict_nao_receita(texto) if texto else "fail"
        else:
            v = "fail"
        snippet = (texto or r.get("detail") or "")[:220].replace("\n", " ")
        print(f"{canal}/{label}: {v} :: {snippet}")


if __name__ == "__main__":
    main()
