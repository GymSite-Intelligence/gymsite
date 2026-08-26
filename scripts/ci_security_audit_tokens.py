"""Fetch Supabase JWTs for security-audit CI (password grant). Writes GITHUB_ENV if set."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def _load_env() -> None:
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / ".env.local", override=False)


def _login(url: str, anon: str, email: str, password: str) -> str:
    base = url.strip().rstrip("/")
    if not base.startswith(("http://", "https://")):
        raise SystemExit(f"Invalid SUPABASE_URL (missing http/https): {base!r}")
    r = httpx.post(
        f"{base}/auth/v1/token?grant_type=password",
        headers={"apikey": anon, "Content-Type": "application/json"},
        json={"email": email, "password": password},
        timeout=30,
    )
    r.raise_for_status()
    token = r.json().get("access_token")
    if not token:
        raise SystemExit("login returned no access_token")
    return str(token)


def _append_github_env(key: str, value: str) -> None:
    path = os.getenv("GITHUB_ENV")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")
    else:
        print(f"{key}={value[:20]}..." if len(value) > 20 else f"{key}={value}")


def main() -> None:
    _load_env()
    url = (os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL") or "").strip()
    anon = (os.getenv("SUPABASE_ANON_KEY") or os.getenv("VITE_SUPABASE_ANON_KEY") or "").strip()
    email_a = (os.getenv("SECURITY_AUDIT_USER_A_EMAIL") or "").strip()
    pass_a = (os.getenv("SECURITY_AUDIT_USER_A_PASSWORD") or "").strip()
    email_b = (os.getenv("SECURITY_AUDIT_USER_B_EMAIL") or "").strip()
    pass_b = (os.getenv("SECURITY_AUDIT_USER_B_PASSWORD") or "").strip()
    fallback_a = (os.getenv("AUDIT_TOKEN_FALLBACK") or "").strip()
    fallback_b = (os.getenv("AUDIT_USER_B_TOKEN_FALLBACK") or "").strip()

    token_a = ""
    token_b = ""

    if url and anon and email_a and pass_a:
        try:
            token_a = _login(url, anon, email_a, pass_a)
        except httpx.HTTPStatusError as exc:
            print(f"warn: login user A failed HTTP {exc.response.status_code}", file=sys.stderr)
    if url and anon and email_b and pass_b:
        try:
            token_b = _login(url, anon, email_b, pass_b)
        except httpx.HTTPStatusError as exc:
            print(f"warn: login user B failed HTTP {exc.response.status_code}", file=sys.stderr)

    if not token_a:
        token_a = fallback_a
    if not token_b:
        token_b = fallback_b

    if not token_a:
        raise SystemExit(
            "No audit token. Set SECURITY_AUDIT_USER_A_* secrets or SECURITY_AUDIT_TOKEN fallback."
        )

    _append_github_env("AUDIT_TOKEN", token_a)
    if token_b:
        _append_github_env("AUDIT_USER_B_TOKEN", token_b)


if __name__ == "__main__":
    main()
