from __future__ import annotations

from tools.security_audit.config import AuditConfig
from tools.security_audit.http_client import RateLimitedClient
from tools.security_audit.logger import AuditLogger
from tools.security_audit.models import Finding, Severity


async def _probe_login(client: RateLimitedClient, config: AuditConfig, email: str) -> tuple[int | None, str, float]:
    ex = await client.post(
        config.login_path,
        headers={"Content-Type": "application/json"},
        json_body={"email": email, "password": config.existing_password},
    )
    return ex.status_code, (ex.response_body or "")[:500], ex.elapsed_ms or 0.0


async def scan_user_enumeration(
    client: RateLimitedClient,
    config: AuditConfig,
    log: AuditLogger,
) -> list[Finding]:
    if config.auth_mode != "supabase":
        return [
            Finding(
                test_id="user_enum_skip",
                title="User enumeration skipped (API auth mode)",
                severity=Severity.INFO,
                description=(
                    "GymSite login is Supabase client-side, not API /auth/*. "
                    "Set auth_mode=supabase and supabase_auth_url to probe Supabase Auth."
                ),
                evidence=f"auth_mode={config.auth_mode} login_path={config.login_path}",
                recommendation="Run user_enum against Supabase /auth/v1/token, not FastAPI.",
            )
        ]

    findings: list[Finding] = []

    exists_status, exists_body, exists_ms = await _probe_login(client, config, config.existing_email)
    missing_status, missing_body, missing_ms = await _probe_login(client, config, config.missing_email)

    if exists_status != missing_status:
        findings.append(
            Finding(
                test_id="user_enum_status",
                title="User enumeration via HTTP status",
                severity=Severity.HIGH,
                description="Different status codes for existing vs missing user.",
                evidence=f"existing={exists_status} missing={missing_status}",
                recommendation="Use identical status codes and generic messages.",
            )
        )

    if exists_body.strip() != missing_body.strip() and exists_body and missing_body:
        leak_words = ("not found", "invalid user", "no account", "does not exist", "unknown user")
        if any(w in missing_body.lower() for w in leak_words) or any(
            w in exists_body.lower() for w in ("wrong password", "incorrect password")
        ):
            findings.append(
                Finding(
                    test_id="user_enum_message",
                    title="User enumeration via error message",
                    severity=Severity.HIGH,
                    description="Distinct error messages reveal account existence.",
                    evidence=f"existing_body={exists_body[:200]} | missing_body={missing_body[:200]}",
                    recommendation="Return generic: invalid credentials.",
                )
            )

    delta = abs(exists_ms - missing_ms)
    if delta > 100:
        findings.append(
            Finding(
                test_id="user_enum_timing",
                title="Potential timing side-channel",
                severity=Severity.MEDIUM,
                description=f"Response time delta {delta:.0f}ms (>100ms threshold).",
                evidence=f"existing={exists_ms:.0f}ms missing={missing_ms:.0f}ms",
                recommendation="Constant-time credential checks; pad processing time.",
            )
        )

    for path, payload_key in (
        (config.forgot_password_path, "email"),
        (config.register_path, "email"),
    ):
        if not path:
            continue
        ex_a = await client.post(
            path,
            headers={"Content-Type": "application/json"},
            json_body={payload_key: config.existing_email},
        )
        ex_b = await client.post(
            path,
            headers={"Content-Type": "application/json"},
            json_body={payload_key: config.missing_email},
        )
        if ex_a.status_code != ex_b.status_code:
            findings.append(
                Finding(
                    test_id="user_enum_forgot",
                    title=f"Enumeration on {path}",
                    severity=Severity.MEDIUM,
                    description="Status differs between known/unknown email.",
                    evidence=f"{ex_a.status_code} vs {ex_b.status_code}",
                    recommendation="Always 200 with generic message.",
                    exchange=ex_a,
                )
            )

    if not findings:
        findings.append(
            Finding(
                test_id="user_enum_ok",
                title="No obvious user enumeration",
                severity=Severity.INFO,
                description="Status, body, timing within thresholds.",
                evidence=f"timing_delta={delta:.0f}ms",
                recommendation="Manual review still recommended.",
            )
        )
    return findings
