"""Resend: contato + e-mail dia 0 da degustação Explorar. Sem preço."""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("gymsite.resend")

_API = "https://api.resend.com"
_FROM_DEFAULT = "GymSite <contato@gymsite.com.br>"


def _key() -> str:
    return (os.getenv("RESEND_API_KEY") or "").strip()


def _from_addr() -> str:
    return (os.getenv("RESEND_FROM") or _FROM_DEFAULT).strip() or _FROM_DEFAULT


def _headers(idempotency_key: str | None = None) -> dict[str, str]:
    h = {
        "Authorization": f"Bearer {_key()}",
        "Content-Type": "application/json",
    }
    if idempotency_key:
        h["Idempotency-Key"] = idempotency_key[:256]
    return h


def _post(path: str, body: dict[str, Any], idempotency_key: str | None = None) -> dict[str, Any]:
    url = f"{_API}{path}"
    with httpx.Client(timeout=20.0) as client:
        r = client.post(url, json=body, headers=_headers(idempotency_key))
    if r.status_code >= 400:
        logger.warning("resend %s falhou status=%s body=%s", path, r.status_code, r.text[:300])
        return {"ok": False, "status": r.status_code}
    try:
        data = r.json()
    except Exception:
        data = {}
    return {"ok": True, "status": r.status_code, "data": data}


def upsert_explorar_contact(email: str) -> dict[str, Any]:
    addr = email.lower().strip()
    created = _post("/contacts", {"email": addr, "unsubscribed": False})
    if created.get("ok"):
        return created
    if created.get("status") in (409, 422):
        return {"ok": True, "status": created.get("status"), "ja_existia": True}
    return created


def send_explorar_welcome(email: str, cidade: str | None, bairro: str | None) -> dict[str, Any]:
    addr = email.lower().strip()
    lugar = ", ".join(p for p in (bairro, cidade) if p) or "o recorte que você olhou"
    html = (
        "<p>Olá,</p>"
        f"<p>Guardamos seu e-mail depois da leitura de <strong>{lugar}</strong> no mapa GymSite.</p>"
        "<p>Vamos te mandar por aqui as próximas leituras desse recorte — sem compromisso de compra.</p>"
        "<p>Abraço,<br/>GymSite</p>"
    )
    return _post(
        "/emails",
        {
            "from": _from_addr(),
            "to": [addr],
            "subject": "Sua leitura do recorte no GymSite",
            "html": html,
            "reply_to": "contato@gymsite.com.br",
        },
        idempotency_key=f"explorar-welcome/{addr}",
    )


def enroll_explorar_lead(
    email: str,
    cidade: str | None = None,
    bairro: str | None = None,
) -> dict[str, Any]:
    if not email or "@" not in email:
        return {"ok": False, "motivo": "email_invalido"}
    if not _key():
        logger.warning("RESEND_API_KEY ausente — lead Explorar sem cadência")
        return {"ok": False, "motivo": "sem_chave"}
    contact = upsert_explorar_contact(email)
    welcome = send_explorar_welcome(email, cidade, bairro)
    return {"ok": bool(welcome.get("ok")), "contact": contact, "welcome": welcome}
