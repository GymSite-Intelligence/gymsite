from __future__ import annotations

import base64
import json
from datetime import datetime, timezone

from tools.security_audit.config import AuditConfig
from tools.security_audit.http_client import RateLimitedClient, token_in_url
from tools.security_audit.logger import AuditLogger
from tools.security_audit.models import Finding, Severity


def _decode_jwt(token: str) -> dict | None:
    parts = token.split(".")
    if len(parts) != 3:
        return None
    try:
        pad = "=" * (-len(parts[0]) % 4)
        header = json.loads(base64.urlsafe_b64decode(parts[0] + pad))
        pad = "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + pad))
        return {"header": header, "payload": payload}
    except (json.JSONDecodeError, ValueError):
        return None


async def scan_jwt(
    client: RateLimitedClient,
    config: AuditConfig,
    log: AuditLogger,
) -> list[Finding]:
    findings: list[Finding] = []
    token = config.token
    if not token:
        findings.append(
            Finding(
                test_id="jwt_skip",
                title="JWT tests skipped",
                severity=Severity.INFO,
                description="No --token provided.",
                evidence="",
                recommendation="Pass Bearer token for JWT audit.",
            )
        )
        return findings

    decoded = _decode_jwt(token)
    if decoded:
        alg = decoded["header"].get("alg", "unknown")
        if str(alg).lower() == "none":
            findings.append(
                Finding(
                    test_id="jwt_alg_none",
                    title="JWT algorithm 'none'",
                    severity=Severity.CRITICAL,
                    description="Token accepts unsigned algorithm.",
                    evidence=f"header={decoded['header']}",
                    recommendation="Reject alg=none; use RS256/HS256 with validation.",
                )
            )
        exp = decoded["payload"].get("exp")
        if exp:
            exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
            ttl_h = (exp_dt - datetime.now(timezone.utc)).total_seconds() / 3600
            if ttl_h > 24:
                findings.append(
                    Finding(
                        test_id="jwt_exp_long",
                        title="JWT expiry exceeds 24h",
                        severity=Severity.MEDIUM,
                        description=f"Token TTL ~{ttl_h:.1f}h.",
                        evidence=f"exp={exp} ({exp_dt.isoformat()})",
                        recommendation="Use short-lived access tokens + refresh rotation.",
                    )
                )

    probe_path = config.resolve_jwt_probe_path()
    ex = await client.get(probe_path, headers=config.auth_headers(token))
    if token_in_url(ex.url):
        findings.append(
            Finding(
                test_id="jwt_url_leak",
                title="JWT transmitted in URL",
                severity=Severity.CRITICAL,
                description="Token appeared in query string.",
                evidence=ex.url,
                recommendation="Use Authorization: Bearer header only.",
                exchange=ex,
            )
        )

    auth_header_used = "authorization" in {k.lower() for k in ex.request_headers}
    if not auth_header_used and ex.status_code == 200:
        findings.append(
            Finding(
                test_id="jwt_header_missing",
                title="Authenticated request without Authorization header",
                severity=Severity.MEDIUM,
                description="Success without Bearer header pattern.",
                evidence=str(ex.request_headers),
                recommendation="Require Authorization header for protected routes.",
                exchange=ex,
            )
        )

    if config.logout_path:
        logout_ex = await client.post(config.logout_path, headers=config.auth_headers(token))
        after = await client.get(probe_path, headers=config.auth_headers(token))
        if after.status_code == 200 and logout_ex.status_code in (200, 204):
            findings.append(
                Finding(
                    test_id="jwt_revocation",
                    title="Token valid after logout",
                    severity=Severity.HIGH,
                    description="JWT still accepted post-logout.",
                    evidence=f"logout={logout_ex.status_code} me={after.status_code}",
                    recommendation="Maintain server-side denylist or rotate session version on logout.",
                    exchange=after,
                )
            )

    if not any(f.severity.value in ("critical", "high", "medium") for f in findings):
        findings.append(
            Finding(
                test_id="jwt_ok",
                title="JWT checks passed baseline",
                severity=Severity.INFO,
                description="No critical JWT issues in configured tests.",
                evidence=f"alg={decoded['header'].get('alg') if decoded else 'n/a'}",
                recommendation="Add refresh-token storage audit separately.",
            )
        )
    return findings
