"""
tools/apollo_client.py — cliente Apollo.io REST (landing leads → Contact + Sequence).

Fluxo espelha sequence-load (MCP Apollo):
  1. POST /contacts (upsert, run_dedupe=true)
  2. POST /emailer_campaigns/{id}/add_contact_ids (se APOLLO_SEQUENCE_ID +
     APOLLO_EMAIL_ACCOUNT_ID setados)

Best-effort: nunca levanta no hot-path de captura de lead.

Env (P-000 §2 — segredos só em .env / Cloud Run):
  APOLLO_API_KEY              obrigatório
  APOLLO_BASE_URL             default https://api.apollo.io/api/v1
  APOLLO_SEQUENCE_ID          sequence/campanha (emailer_campaign)
  APOLLO_EMAIL_ACCOUNT_ID     caixa remetente (ID) — ou use APOLLO_SENDER_EMAIL
  APOLLO_SENDER_EMAIL         ex: suporte@gymsite.com.br — resolve ID via GET /email_accounts
  APOLLO_SYNC_ENABLED         default true

Ver docs/handoffs/HANDOFF_APOLLO_MARKETING.md e .env.production.example.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger("gymsite.apollo")

# Canônico: mesmo prefixo que services/apollo_crm_sync.py
_DEFAULT_BASE = "https://api.apollo.io/api/v1"
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


def _headers(key: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": key,
    }


def resolve_email_account_id(key: str | None = None) -> str | None:
    """Resolve APOLLO_EMAIL_ACCOUNT_ID via env ou lookup por APOLLO_SENDER_EMAIL."""
    direct = (os.getenv("APOLLO_EMAIL_ACCOUNT_ID") or "").strip()
    if direct:
        return direct
    sender = (os.getenv("APOLLO_SENDER_EMAIL") or "").strip().lower()
    if not sender:
        return None
    try:
        import httpx

        k = (key or _api_key()).strip()
        if not k:
            return None
        with httpx.Client(timeout=_TIMEOUT_S) as client:
            resp = client.get(f"{_base_url()}/email_accounts", headers=_headers(k))
        if resp.status_code >= 400:
            logger.warning("Apollo email_accounts HTTP %s: %s", resp.status_code, resp.text[:200])
            return None
        data = resp.json() if resp.content else {}
        for acct in data.get("email_accounts") or []:
            addr = (acct.get("email") or acct.get("address") or "").strip().lower()
            if addr == sender:
                acct_id = acct.get("id")
                if acct_id:
                    logger.info("Apollo sender %s → account_id %s", sender, acct_id)
                    return str(acct_id)
        logger.warning("Apollo: caixa %s nao encontrada nas email_accounts", sender)
    except Exception as e:  # noqa: BLE001
        logger.warning("Apollo resolve_email_account_id falhou: %s", e)
    return None


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
    """Upsert lead como Contact + enrollment opcional na sequence.

    Retorno:
      ok, contact_id, sequence_enrolled, sequence_id, skipped|error
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
        "last_name": last or first,
        "email": email.lower().strip(),
        "organization_name": (empresa or "").strip() or None,
        "present_raw_address": ", ".join(p for p in (bairro, cidade) if p) or None,
        "label_names": [label, fonte],
        "run_dedupe": True,
    }
    if telefone:
        payload["direct_phone"] = telefone
    payload = {k: v for k, v in payload.items() if v not in (None, "", [])}

    headers = _headers(key)
    seq_id = (os.getenv("APOLLO_SEQUENCE_ID") or "").strip()

    try:
        with httpx.Client(timeout=_TIMEOUT_S) as client:
            resp = client.post(f"{_base_url()}/contacts", headers=headers, json=payload)
        if resp.status_code >= 400:
            logger.warning("Apollo contacts HTTP %s: %s", resp.status_code, resp.text[:300])
            return {"ok": False, "error": f"HTTP {resp.status_code}", "detail": resp.text[:200]}

        data = resp.json() if resp.content else {}
        contact = data.get("contact") or data.get("person") or {}
        contact_id = contact.get("id")

        seq_result: dict[str, Any] = {"sequence_enrolled": False, "sequence_id": seq_id or None}
        if contact_id and seq_id:
            seq_result = _add_to_sequence(contact_id, seq_id, headers)

        logger.info(
            "Apollo upsert ok contact_id=%s email=%s sequence_enrolled=%s",
            contact_id, email, seq_result.get("sequence_enrolled"),
        )
        return {
            "ok": True,
            "contact_id": contact_id,
            **seq_result,
        }
    except Exception as e:  # noqa: BLE001
        logger.warning("Apollo upsert falhou: %s", e)
        return {"ok": False, "error": str(e)[:200]}


def _add_to_sequence(contact_id: str, sequence_id: str, headers: dict) -> dict[str, Any]:
    """Enrollment na sequence (equiv. sequence-load passo 6)."""
    email_account_id = resolve_email_account_id(key=headers.get("X-Api-Key"))
    if not email_account_id:
        logger.warning(
            "APOLLO_EMAIL_ACCOUNT_ID ausente — contato %s NAO entra na sequence %s",
            contact_id, sequence_id,
        )
        return {
            "sequence_enrolled": False,
            "sequence_id": sequence_id,
            "sequence_error": "sem APOLLO_EMAIL_ACCOUNT_ID nem APOLLO_SENDER_EMAIL resolvido",
        }

    try:
        import httpx

        with httpx.Client(timeout=_TIMEOUT_S) as client:
            resp = client.post(
                f"{_base_url()}/emailer_campaigns/{sequence_id}/add_contact_ids",
                headers=headers,
                json={
                    "contact_ids": [contact_id],
                    "emailer_campaign_id": sequence_id,
                    "send_email_from_email_account_id": email_account_id,
                    "sequence_active_in_other_campaigns": False,
                },
            )
        if resp.status_code >= 400:
            logger.warning(
                "Apollo add_to_sequence HTTP %s: %s", resp.status_code, resp.text[:200]
            )
            return {
                "sequence_enrolled": False,
                "sequence_id": sequence_id,
                "sequence_error": f"HTTP {resp.status_code}",
            }
        logger.info("contato %s adicionado a sequence %s", contact_id, sequence_id)
        return {"sequence_enrolled": True, "sequence_id": sequence_id}
    except Exception as e:  # noqa: BLE001
        logger.warning("Apollo add_to_sequence falhou: %s", e)
        return {
            "sequence_enrolled": False,
            "sequence_id": sequence_id,
            "sequence_error": str(e)[:200],
        }
