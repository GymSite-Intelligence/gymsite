#!/usr/bin/env python3
"""Re-sync leads únicos (por email) para Apollo + sequence.

Uso:
  .venv/Scripts/python.exe tools/resync_leads_apollo.py
  .venv/Scripts/python.exe tools/resync_leads_apollo.py --dry-run

Requer: APOLLO_API_KEY, APOLLO_SEQUENCE_ID, APOLLO_SENDER_EMAIL ou APOLLO_EMAIL_ACCOUNT_ID
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

_OK_STATUSES = frozenset({"sincronizado", "sincronizado_sequencia"})


def _unique_leads_pending(rows: list[dict]) -> list[dict]:
    """Último registro por email (lower) que ainda não sincronizou OK."""
    by_email: dict[str, dict] = {}
    for row in sorted(rows, key=lambda r: r.get("created_at") or ""):
        email = (row.get("email") or "").strip().lower()
        if not email:
            continue
        status = row.get("apollo_sync_status") or "pendente"
        if status in _OK_STATUSES and row.get("apollo_contact_id"):
            by_email.pop(email, None)
            continue
        by_email[email] = row
    return list(by_email.values())


def main() -> int:
    p = argparse.ArgumentParser(description="Re-sync leads únicos → Apollo")
    p.add_argument("--dry-run", action="store_true", help="Só lista, não chama Apollo")
    args = p.parse_args()

    from supabase import create_client
    from tools.db_schema import tbl
    from tools.apollo_client import resolve_email_account_id, sync_lead_to_apollo

    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        print("ERRO: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY ausentes")
        return 1

    sender = (os.getenv("APOLLO_SENDER_EMAIL") or "").strip()
    acct = resolve_email_account_id()
    print(f"sender={sender or '(unset)'} account_id={acct or '(nao resolvido)'}")

    sb = create_client(url, key)
    rows = (
        tbl(sb, "leads")
        .select("id,email,nome,telefone,cidade,bairro,perfil,fonte,apollo_sync_status,apollo_contact_id,created_at")
        .order("created_at")
        .execute()
    ).data or []

    pending = _unique_leads_pending(rows)
    print(f"leads total={len(rows)} unique_pending={len(pending)}")
    for row in pending:
        print(f"  - {row['email']} ({row.get('apollo_sync_status')}) id={row['id']}")

    if args.dry_run:
        return 0
    if not pending:
        print("Nada a reenviar.")
        return 0

    ok = fail = 0
    for row in pending:
        resultado = sync_lead_to_apollo(
            nome=row.get("nome") or "",
            email=row["email"],
            telefone=row.get("telefone"),
            cidade=row.get("cidade"),
            bairro=row.get("bairro"),
            perfil=row.get("perfil"),
            fonte=row.get("fonte") or "landing-getgymsite",
        )
        if resultado.get("ok"):
            if resultado.get("sequence_enrolled"):
                status = "sincronizado_sequencia"
            elif resultado.get("sequence_id"):
                status = "sincronizado_sem_sequencia"
            else:
                status = "sincronizado"
            ok += 1
        else:
            status = "erro"
            fail += 1
        tbl(sb, "leads").update({
            "apollo_sync_status": status,
            "apollo_contact_id": resultado.get("contact_id"),
            "apollo_synced_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", row["id"]).execute()
        print(
            f"{row['email']}: {status}"
            + (f" contact={resultado.get('contact_id')}" if resultado.get("contact_id") else "")
            + (f" err={resultado.get('error') or resultado.get('sequence_error')}" if status == "erro" else "")
        )

    print(f"done ok={ok} fail={fail}")
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
