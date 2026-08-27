#!/usr/bin/env python3
"""Push GitHub Actions secrets for tools/security_audit (manual workflow).

Preferred (JWT refreshed each CI run — store email/password, not JWT):
  python scripts/setup_github_security_audit_secrets.py --bootstrap

Or existing accounts:
  set SECURITY_AUDIT_USER_A_EMAIL=...
  set SECURITY_AUDIT_USER_A_PASSWORD=...
  python scripts/setup_github_security_audit_secrets.py --push-credentials

Legacy (JWT expires ~1h — avoid for CI):
  python scripts/setup_github_security_audit_secrets.py --token-a "eyJ..."

Requires `gh auth login` + local .env with SUPABASE_SERVICE_ROLE_KEY for --bootstrap.
"""
from __future__ import annotations

import argparse
import os
import secrets
import subprocess
import string
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
API_BASE = "https://api.getgymsite.com.br"
# enforce_company_domain() allows non-@vectracargo.com.br only when app_metadata.origem is set.
AUDIT_APP_METADATA = {"origem": "gymsite"}
DEFAULT_EMAIL_A = "gymsite-security-audit-a@getgymsite.com.br"
DEFAULT_EMAIL_B = "gymsite-security-audit-b@getgymsite.com.br"


def _load_env() -> None:
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / ".env.local", override=False)


def _supabase_base() -> tuple[str, str, str]:
    url = (os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL") or "").strip().rstrip("/")
    anon = (
        os.getenv("VITE_SUPABASE_ANON_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
        or os.getenv("SUPABASE_PUBLISHABLE_KEY")
        or ""
    ).strip()
    service = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not anon:
        raise SystemExit("Missing SUPABASE_URL and anon key in .env")
    return url, anon, service


def _random_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _supabase_auth(url: str, anon: str, email: str, password: str) -> str:
    r = httpx.post(
        f"{url}/auth/v1/token?grant_type=password",
        headers={"apikey": anon, "Content-Type": "application/json"},
        json={"email": email, "password": password},
        timeout=30,
    )
    if r.status_code >= 400:
        raise SystemExit(f"Supabase login failed for {email}: HTTP {r.status_code} {r.text[:200]}")
    token = r.json().get("access_token")
    if not token:
        raise SystemExit(f"Supabase login for {email} returned no access_token")
    return str(token)


def _try_supabase_auth(url: str, anon: str, email: str, password: str) -> str | None:
    r = httpx.post(
        f"{url}/auth/v1/token?grant_type=password",
        headers={"apikey": anon, "Content-Type": "application/json"},
        json={"email": email, "password": password},
        timeout=30,
    )
    if r.status_code >= 400:
        print(f"warn: login {email} HTTP {r.status_code} — run supabase_auth_audit_users_token_patch.sql")
        return None
    token = r.json().get("access_token")
    if not token:
        print(f"warn: login {email} returned no access_token")
        return None
    return str(token)


def _admin_headers(service: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {service}", "apikey": service, "Content-Type": "application/json"}


def _admin_find_user(url: str, service: str, email: str) -> dict | None:
    headers = _admin_headers(service)
    target = email.strip().lower()
    for page in range(1, 20):
        listed = httpx.get(
            f"{url}/auth/v1/admin/users",
            headers=headers,
            params={"page": page, "per_page": 200},
            timeout=30,
        )
        if listed.status_code >= 400:
            return None
        batch = listed.json().get("users") or []
        if not batch:
            break
        for user in batch:
            if (user.get("email") or "").strip().lower() == target:
                return user
    return None


def _admin_delete_user(url: str, service: str, user_id: str) -> None:
    headers = _admin_headers(service)
    proc = httpx.delete(f"{url}/auth/v1/admin/users/{user_id}", headers=headers, timeout=30)
    if proc.status_code >= 400:
        raise SystemExit(f"admin delete failed: {proc.status_code} {proc.text[:200]}")


def _admin_user_payload(email: str, password: str) -> dict:
    return {
        "email": email,
        "password": password,
        "email_confirm": True,
        "app_metadata": dict(AUDIT_APP_METADATA),
    }


def _admin_recreate_user(url: str, service: str, email: str, password: str) -> None:
    headers = _admin_headers(service)
    existing = _admin_find_user(url, service, email)
    if existing:
        identities = existing.get("identities") or []
        if identities:
            _admin_delete_user(url, service, str(existing["id"]))
            print(f"deleted existing user {email} (broken or recreate)")
        else:
            raise SystemExit(
                f"user {email} exists without email identity (providers=[]). "
                "Run scripts/supabase_auth_audit_users_fix.sql in SQL Editor, then --bootstrap again."
            )

    payload = _admin_user_payload(email, password)
    create = httpx.post(f"{url}/auth/v1/admin/users", headers=headers, json=payload, timeout=30)
    if create.status_code in (200, 201):
        body = create.json()
        providers = [i.get("provider") for i in (body.get("identities") or [])]
        if "email" not in providers:
            raise SystemExit(f"created {email} but no email identity — run supabase_auth_audit_users_fix.sql")
        print(f"created auth user {email} (app_metadata.origem=gymsite, providers={providers})")
        return
    raise SystemExit(
        f"admin create user failed for {email}: {create.status_code} {create.text[:200]}. "
        "If 500 checking email: run scripts/supabase_auth_audit_users_fix.sql (DELETE audit users only), then retry."
    )


def _admin_upsert_user(url: str, service: str, email: str, password: str) -> None:
    _admin_recreate_user(url, service, email, password)


def _fetch_relatorio_id(token: str) -> str | None:
    r = httpx.get(
        f"{API_BASE}/api/relatorios",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if r.status_code >= 400:
        print(f"warn: GET /api/relatorios HTTP {r.status_code} — skip relatorio UUID secret")
        return None
    data = r.json()
    items = data if isinstance(data, list) else data.get("items") or data.get("relatorios") or []
    if not items:
        print("warn: user A has no relatorios — IDOR owner probe skipped until one exists")
        return None
    first = items[0]
    rid = first.get("id") if isinstance(first, dict) else None
    if rid:
        print(f"found relatorio UUID for user A")
    return str(rid) if rid else None


def _gh_secret_set(name: str, value: str, *, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] would set secret {name} ({len(value)} chars)")
        return
    proc = subprocess.run(
        ["gh", "secret", "set", name, "--body", value],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(f"gh secret set {name} failed: {proc.stderr.strip() or proc.stdout}")
    print(f"ok secret {name}")


def _push_credentials(
    *,
    email_a: str,
    pass_a: str,
    email_b: str | None,
    pass_b: str | None,
    rel_a: str | None,
    dry_run: bool,
) -> None:
    _gh_secret_set("SECURITY_AUDIT_USER_A_EMAIL", email_a, dry_run=dry_run)
    _gh_secret_set("SECURITY_AUDIT_USER_A_PASSWORD", pass_a, dry_run=dry_run)
    if email_b and pass_b:
        _gh_secret_set("SECURITY_AUDIT_USER_B_EMAIL", email_b, dry_run=dry_run)
        _gh_secret_set("SECURITY_AUDIT_USER_B_PASSWORD", pass_b, dry_run=dry_run)
    if rel_a:
        _gh_secret_set("SECURITY_AUDIT_RELATORIO_USER_A", rel_a, dry_run=dry_run)


def main() -> None:
    p = argparse.ArgumentParser(description="Configure GitHub secrets for security-audit workflow")
    p.add_argument("--bootstrap", action="store_true", help="Create audit users via service role + push creds")
    p.add_argument("--push-credentials", action="store_true", help="Push email/password from env to gh secrets")
    p.add_argument("--token-a", help="Legacy: JWT user A")
    p.add_argument("--token-b", help="Legacy: JWT user B")
    p.add_argument("--relatorio-a", help="Relatorio UUID owned by user A")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    _load_env()
    url, anon, service = _supabase_base()

    if args.bootstrap:
        if not service:
            raise SystemExit("--bootstrap needs SUPABASE_SERVICE_ROLE_KEY in .env")
        email_a = (os.getenv("SECURITY_AUDIT_USER_A_EMAIL") or DEFAULT_EMAIL_A).strip()
        email_b = (os.getenv("SECURITY_AUDIT_USER_B_EMAIL") or DEFAULT_EMAIL_B).strip()
        pass_a = _random_password()
        pass_b = _random_password()
        _admin_upsert_user(url, service, email_a, pass_a)
        _admin_upsert_user(url, service, email_b, pass_b)
        _push_credentials(
            email_a=email_a,
            pass_a=pass_a,
            email_b=email_b,
            pass_b=pass_b,
            rel_a=None,
            dry_run=args.dry_run,
        )
        if not args.dry_run:
            print(f"gh secrets set (save locally if login fails):\n"
                  f"  SECURITY_AUDIT_USER_A_PASSWORD={pass_a}\n"
                  f"  SECURITY_AUDIT_USER_B_PASSWORD={pass_b}")
        token_a = _try_supabase_auth(url, anon, email_a, pass_a)
        rel_a = _fetch_relatorio_id(token_a) if token_a else None
        if rel_a:
            _gh_secret_set("SECURITY_AUDIT_RELATORIO_USER_A", rel_a, dry_run=args.dry_run)
        if token_a:
            print("login OK — gh secrets ready")
        else:
            print(
                "users created + gh creds pushed. login still blocked.\n"
                "1) scripts/supabase_auth_find_bad_users.sql — if bad_rows > 0:\n"
                "   scripts/supabase_auth_repair_null_tokens.sql\n"
                "2) scripts/supabase_auth_audit_users_token_patch.sql (audit rows)\n"
                "3) re-test: set env passwords above + --push-credentials"
            )
        print("trigger: gh workflow run security-audit.yml (after token patch)")
        return

    if args.push_credentials:
        email_a = (os.getenv("SECURITY_AUDIT_USER_A_EMAIL") or "").strip()
        pass_a = (os.getenv("SECURITY_AUDIT_USER_A_PASSWORD") or "").strip()
        email_b = (os.getenv("SECURITY_AUDIT_USER_B_EMAIL") or "").strip() or None
        pass_b = (os.getenv("SECURITY_AUDIT_USER_B_PASSWORD") or "").strip() or None
        rel_a = (args.relatorio_a or os.getenv("SECURITY_AUDIT_RELATORIO_USER_A") or "").strip() or None
        if not email_a or not pass_a:
            raise SystemExit("Set SECURITY_AUDIT_USER_A_EMAIL and SECURITY_AUDIT_USER_A_PASSWORD")
        if (email_b and not pass_b) or (pass_b and not email_b):
            raise SystemExit("User B needs both EMAIL and PASSWORD")
        if not rel_a:
            token_a = _supabase_auth(url, anon, email_a, pass_a)
            rel_a = _fetch_relatorio_id(token_a)
        _push_credentials(
            email_a=email_a,
            pass_a=pass_a,
            email_b=email_b,
            pass_b=pass_b,
            rel_a=rel_a,
            dry_run=args.dry_run,
        )
        print("done.")
        return

    token_a = (args.token_a or os.getenv("SECURITY_AUDIT_TOKEN") or "").strip()
    token_b = (args.token_b or os.getenv("SECURITY_AUDIT_USER_B_TOKEN") or "").strip()
    rel_a = (args.relatorio_a or os.getenv("SECURITY_AUDIT_RELATORIO_USER_A") or "").strip()
    if not token_a:
        raise SystemExit("Use --bootstrap, --push-credentials, or --token-a")
    _gh_secret_set("SECURITY_AUDIT_TOKEN", token_a, dry_run=args.dry_run)
    if token_b:
        _gh_secret_set("SECURITY_AUDIT_USER_B_TOKEN", token_b, dry_run=args.dry_run)
    if rel_a:
        _gh_secret_set("SECURITY_AUDIT_RELATORIO_USER_A", rel_a, dry_run=args.dry_run)
    print("warn: JWT secrets expire — prefer --bootstrap for CI")


if __name__ == "__main__":
    main()
