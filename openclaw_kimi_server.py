"""
OpenClaw Kimi Server — proxy HTTP para o GymSite (A0 / A8).

Contrato GymSite (tools/kimi_research.py):
  POST /v1/kimi/search  { "query": "...", "source": "gymsite_a0" }
  → 200 { "result": "markdown..." }
  Authorization: Bearer <OPENCLAW_TOKEN>

Backends (KIMI_BACKEND):
  - groq     — Groq Compound (busca web nativa; recomendado)
  - moonshot — API Kimi/Moonshot (web_search)
  - ollama   — Ollama local (sem busca web)

Env:
  KIMI_BACKEND=groq|ollama|moonshot
  GROQ_API_KEY, GROQ_MODEL=groq/compound-mini, GROQ_BASE_URL
  OLLAMA_BASE_URL, OLLAMA_MODEL
  KIMI_API_KEY, OPENCLAW_TOKEN, PORT, KIMI_TIMEOUT_SEC

Run (raiz do repo):
  uvicorn openclaw_kimi_server:app --host 0.0.0.0 --port 8001 --reload
"""
from __future__ import annotations

import os
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

# override=True: .env ganha sobre $env:KIMI_BACKEND=ollama legado no PowerShell
load_dotenv(override=True)


def _env(key: str, default: str = "") -> str:
    return (os.getenv(key) or default).strip()


def _env_float(key: str, default: float) -> float:
    try:
        return float(_env(key, str(default)))
    except ValueError:
        return default


app = FastAPI(title="OpenClaw Kimi Server", version="1.2.1")
_bearer = HTTPBearer(auto_error=False)

_SYSTEM_PROMPT = (
    "Você é um analista de mercado fitness no Brasil. "
    "Responda em português (Brasil), em markdown estruturado. "
    "Se não tiver dados atualizados da web, deixe explícito e use raciocínio "
    "qualitativo + fontes públicas conhecidas (IBGE, tendências setoriais). "
    "Não invente números precisos sem base."
)


class KimiSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    source: str = "gymsite_a0"


class KimiSearchResponse(BaseModel):
    result: str
    backend: str | None = None


def _resolved_backend() -> Literal["groq", "ollama", "moonshot"]:
    backend = _env("KIMI_BACKEND", "groq").lower()
    if backend in ("groq", "groqcloud"):
        return "groq"
    if backend in ("ollama", "local"):
        return "ollama"
    if backend == "moonshot":
        return "moonshot"
    if _env("GROQ_API_KEY"):
        return "groq"
    if not _env("KIMI_API_KEY") and _env("OLLAMA_BASE_URL", "http://127.0.0.1:11434"):
        return "ollama"
    return "moonshot"


def _require_auth(creds: HTTPAuthorizationCredentials | None) -> None:
    if not _env("OPENCLAW_TOKEN"):
        return
    if not creds or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer token obrigatório")
    if creds.credentials != _env("OPENCLAW_TOKEN"):
        raise HTTPException(status_code=403, detail="Token inválido")


def _extract_openai_message_text(data: dict[str, Any]) -> str:
    choices = data.get("choices") or []
    if not choices:
        return ""
    msg = (choices[0] or {}).get("message") or {}
    content = msg.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                t = block.get("text", "")
                if t:
                    parts.append(str(t))
        return "\n".join(parts).strip()
    return ""


def _extract_ollama_message_text(data: dict[str, Any]) -> str:
    msg = data.get("message") or {}
    content = msg.get("content")
    return content.strip() if isinstance(content, str) else ""


async def _ollama_reachable() -> bool:
    base = _env("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{base}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


async def _call_ollama(query: str, source: str) -> str:
    ollama_base = _env("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    ollama_model = _env("OLLAMA_MODEL", "llama3.2:3b")
    timeout = _env_float("KIMI_TIMEOUT_SEC", 120)
    system = f"{_SYSTEM_PROMPT} Cliente: {source}. Backend: Ollama local (sem web search)."
    payload = {
        "model": ollama_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": query},
        ],
        "stream": False,
        "options": {"temperature": 0.4, "num_ctx": 4096},
    }
    url = f"{ollama_base}/api/chat"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload)
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Ollama HTTP {resp.status_code}: {resp.text[:300]}",
        )
    text = _extract_ollama_message_text(resp.json())
    if not text:
        raise HTTPException(status_code=502, detail="Ollama respondeu sem conteúdo")
    return (
        f"<!-- backend:ollama model:{ollama_model} -->\n\n"
        f"{text}\n\n---\n*Gerado via Ollama local. Sem busca web; valide dados críticos.*"
    )


async def _call_groq(query: str, source: str) -> str:
    groq_key = _env("GROQ_API_KEY")
    groq_model = _env("GROQ_MODEL", "groq/compound-mini")
    groq_base = _env("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
    timeout = _env_float("KIMI_TIMEOUT_SEC", 120)
    if not groq_key:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY não configurada (KIMI_BACKEND=groq)",
        )

    system = (
        f"{_SYSTEM_PROMPT} Use busca web para dados recentes do Brasil. "
        f"Cite fontes (URLs) quando possível. Cliente: {source}."
    )
    payload: dict[str, Any] = {
        "model": groq_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": query},
        ],
        "temperature": 0.3,
    }

    url = f"{groq_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload, headers=headers)

    if resp.status_code >= 400:
        detail = resp.text[:500]
        # Fallback: modelo sem compound (sem web search)
        if "compound" in groq_model.lower() and resp.status_code in (400, 404, 422, 429):
            payload["model"] = _env("GROQ_FALLBACK_MODEL", "llama-3.1-8b-instant")
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"Groq HTTP {resp.status_code}: {resp.text[:300]}",
            )

    text = _extract_openai_message_text(resp.json())
    if not text:
        raise HTTPException(status_code=502, detail="Groq respondeu sem conteúdo")
    model_used = payload.get("model", groq_model)
    return (
        f"<!-- backend:groq model:{model_used} -->\n\n"
        f"{text}\n\n---\n*Pesquisa via Groq ({model_used}).*"
    )


async def _call_moonshot(query: str, source: str) -> str:
    kimi_key = _env("KIMI_API_KEY")
    kimi_model = _env("KIMI_MODEL", "kimi-latest")
    kimi_base = _env("KIMI_BASE_URL", "https://api.moonshot.cn/v1").rstrip("/")
    timeout = _env_float("KIMI_TIMEOUT_SEC", 120)
    if not kimi_key:
        raise HTTPException(
            status_code=500,
            detail="KIMI_API_KEY não configurada (ou use KIMI_BACKEND=ollama)",
        )

    system = f"{_SYSTEM_PROMPT} Inclua URLs de fontes quando usar busca web. Cliente: {source}."

    payload: dict[str, Any] = {
        "model": kimi_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": query},
        ],
        "temperature": 0.3,
        "tools": [
            {"type": "builtin_function", "function": {"name": "$web_search"}},
        ],
    }

    url = f"{kimi_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {kimi_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload, headers=headers)

    if resp.status_code >= 400:
        detail = resp.text[:500]
        if resp.status_code in (400, 422) and "tool" in detail.lower():
            payload.pop("tools", None)
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code >= 400:
                raise HTTPException(
                    status_code=502,
                    detail=f"Moonshot HTTP {resp.status_code}: {resp.text[:300]}",
                )
        else:
            raise HTTPException(
                status_code=502,
                detail=f"Moonshot HTTP {resp.status_code}: {detail}",
            )

    text = _extract_openai_message_text(resp.json())
    if not text:
        raise HTTPException(status_code=502, detail="Moonshot respondeu sem conteúdo")
    return text


async def _run_search(query: str, source: str) -> tuple[str, str]:
    backend = _resolved_backend()
    if backend == "groq":
        return await _call_groq(query, source), "groq"
    if backend == "ollama":
        return await _call_ollama(query, source), "ollama"
    return await _call_moonshot(query, source), "moonshot"


@app.get("/health")
async def health() -> dict[str, Any]:
    load_dotenv(override=True)
    backend = _resolved_backend()
    ollama_ok = await _ollama_reachable()
    groq_key = _env("GROQ_API_KEY")
    kimi_key = _env("KIMI_API_KEY")
    ok = (
        (backend == "groq" and bool(groq_key))
        or (backend == "ollama" and ollama_ok)
        or (backend == "moonshot" and bool(kimi_key))
    )
    if backend == "groq":
        model = _env("GROQ_MODEL", "groq/compound-mini")
        base = _env("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    elif backend == "ollama":
        model = _env("OLLAMA_MODEL", "llama3.2:3b")
        base = _env("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    else:
        model = _env("KIMI_MODEL", "kimi-latest")
        base = _env("KIMI_BASE_URL", "https://api.moonshot.cn/v1")
    return {
        "ok": ok,
        "backend": backend,
        "kimi_backend_env": _env("KIMI_BACKEND", "groq"),
        "groq_configured": bool(groq_key),
        "groq_model": _env("GROQ_MODEL", "groq/compound-mini"),
        "kimi_configured": bool(kimi_key),
        "ollama_configured": ollama_ok,
        "ollama_base_url": _env("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        "ollama_model": _env("OLLAMA_MODEL", "llama3.2:3b"),
        "auth_configured": bool(_env("OPENCLAW_TOKEN")),
        "model": model,
        "base_url": base,
    }


@app.post("/v1/kimi/search", response_model=KimiSearchResponse)
async def kimi_search(
    body: KimiSearchRequest,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> KimiSearchResponse:
    _require_auth(creds)
    result, backend = await _run_search(body.query.strip(), body.source)
    return KimiSearchResponse(result=result, backend=backend)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8001"))
    uvicorn.run("openclaw_kimi_server:app", host="0.0.0.0", port=port, reload=True)
