"""Verificação do Cloudflare Turnstile (anti-bot) para o endpoint público da
análise gratuita (N3).

Fluxo: o front renderiza o widget Turnstile e manda o token no POST; aqui
validamos contra o siteverify da Cloudflare usando TURNSTILE_SECRET.

Fail-open vs fail-closed: este endpoint GASTA dinheiro (SearchAPI/Gemini) por
run, então é **fail-closed** — sem secret configurada OU verificação falha →
nega. Em dev, defina TURNSTILE_SECRET com a test key da Cloudflare
(1x0000000000000000000000000000000AA) que sempre passa.
"""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger("gymsite.turnstile")

_SITEVERIFY = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verificar_turnstile(token: str | None, remote_ip: str | None = None) -> bool:
    """True se o token Turnstile é válido. Fail-closed em qualquer erro/ausência."""
    secret = (os.getenv("TURNSTILE_SECRET") or "").strip()
    if not secret:
        logger.error("TURNSTILE_SECRET ausente — negando (fail-closed)")
        return False
    if not token:
        return False

    data = {"secret": secret, "response": token}
    if remote_ip:
        data["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient(timeout=10) as c:
            resp = await c.post(_SITEVERIFY, data=data)
        out = resp.json()
        ok = bool(out.get("success"))
        if not ok:
            logger.warning("Turnstile rejeitou: %s", out.get("error-codes"))
        return ok
    except Exception as exc:  # noqa: BLE001
        logger.warning("Turnstile siteverify falhou: %s", exc)
        return False
