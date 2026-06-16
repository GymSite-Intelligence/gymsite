"""
tools/apollo_client.py — cliente minimo da Apollo.io REST API (v1).

Faz upsert de um lead da landing como Contact no Apollo e (opcional) adiciona
a uma sequence/lista. Best-effort: qualquer falha retorna {"ok": False, ...}
para o chamador decidir — NUNCA levanta excecao no hot-path de captura de lead.

## Segredo (NAO COMITAR)
A chave da API vive SOMENTE em variavel de ambiente:

    APOLLO_API_KEY=...            # https://app.apollo.io/#/settings/integrations/api

Opcionais:
    APOLLO_BASE_URL=https://api.apollo.io/v1   (default)
    APOLLO_SEQUENCE_ID=...       # se setado, tenta adicionar o contato a sequence
    APOLLO_SYNC_ENABLED=true     # liga/desliga o sync sem mexer no codigo

Docs: https://docs.apollo.io/reference (People / Contacts endpoints).
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger("gymsite.apollo")

_DEFAULT_BASE = "https://api.apollo.io/v1"
_TIMEOUT_S = 12.0


def _enabled() -> bool:
    return (os.getenv("APOLLO_SYNC_ENABLED", "true") or "").strip().lower() not in (
        "0", "false", "no", "off",
    )


def _api_key() -> str:
    return (os.getenv("APOLLO_API_KEY") or "").strip()


def _base_url() -> str:
    return (os.getenv("APOLLO_BASE_URL") or _DEFAULT_BASE).rstrip("/")


def _split_nome(nome: str) -> tuple[str, str]:
    partes = (nome or "").strip().split()
    if not partes:
        return "", ""
    if len(partes) == 1:
        return partes[0], ""
    return partes[0], " ".join(partes[1:])


def sync_lead_to_apollo(
    *,
    nome: str,
    email: str,
    telefone: Optional[str] = None,
    empresa: Optional[str] = None,
    cidade: Optional[str] = None,
    bairro: Optional[str] = None,
    perfil: Optional[str] = None,
    fonte: str = "landing-getgymsite",
) -> dict[str, Any]:
    """Upsert de um lead como Contact no Apollo.

    Retorna {"ok": bool, "contact_id": str|None, "skipped"/"error": str}.
    """
    if not _enabled():
        return {"ok": False, "skipped": "APOLLO_SYNC_ENABLED=false"}

    key = _api_key()
    if not key:
        logger.info("APOLLO_API_KEY ausente — sync ignorado (lead salvo localmente)")
        return {"ok": False, "skipped": "sem APOLLO_API_KEY"}

    try:
        import httpx
    except Exception:  # noqa: BLE001
        return {"ok": False, "error": "httpx nao instalado"}

    first, last = _split_nome(nome)
    label = f"GymSite · {perfil or 'lead'}"
    payload: dict[str, Any] = {
        "first_name": first,
        "last_name": last,
        "email": email,
        "title": (empresa or "").strip() or None,
        # campos livres que ajudam a segmentar no Apollo
        "present_raw_address": ", ".join(p for p in (bairro, cidade) if p) or None,
        "label_names": [label, fonte],
    }
    if telefone:
        payload["contact_phone_numbers"] = [{"raw_number": telefone}]
    payload = {k: v for k, v in payload.items() if v not in (None, "", [])}

    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": key,
    }

    try:
        with httpx.Client(timeout=_TIMEOUT_S) as client:
            # Endpoint de upsert de contato. Apollo aceita a key tanto no header
            # X-Api-Key quanto no corpo (api_key); mandamos no header por higiene.
            resp = client.post(
                f"{_base_url()}/contacts",
                headers=headers,
                json=payload,
            )
        if resp.status_code >= 400:
            logger.warning("Apollo upsert HTTP %s: %s", resp.status_code, resp.text[:300])
            return {"ok": False, "error": f"HTTP {resp.status_code}"}

        data = resp.json() if resp.content else {}
        contact = data.get("contact") or data.get("person") or {}
        contact_id = contact.get("id")

        seq_id = (os.getenv("APOLLO_SEQUENCE_ID") or "").strip()
        if contact_id and seq_id:
            _add_to_sequence(contact_id, seq_id, headers)

        logger.info("Apollo upsert ok contact_id=%s email=%s", contact_id, email)
        return {"ok": True, "contact_id": contact_id}
    except Exception as e:  # noqa: BLE001
        logger.warning("Apollo upsert falhou: %s", e)
        return {"ok": False, "error": str(e)[:200]}


def _add_to_sequence(contact_id: str, sequence_id: str, headers: dict) -> None:
    """Best-effort: adiciona o contato a uma Apollo sequence.
    Falha silenciosa — o lead ja esta no Apollo de qualquer forma."""
    try:
        import httpx

        with httpx.Client(timeout=_TIMEOUT_S) as client:
            client.post(
                f"{_base_url()}/emailer_campaigns/{sequence_id}/add_contact_ids",
                headers=headers,
                json={"contact_ids": [contact_id], "send_email_from_email_account_id": None},
            )
    except Exception as e:  # noqa: BLE001
        logger.info("Apollo add_to_sequence ignorado: %s", e)
