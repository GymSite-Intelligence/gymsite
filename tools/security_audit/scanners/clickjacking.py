from __future__ import annotations

from tools.security_audit.config import AuditConfig
from tools.security_audit.http_client import RateLimitedClient
from tools.security_audit.logger import AuditLogger
from tools.security_audit.models import Finding, Severity

PROTECTED_VALUES = {"deny", "sameorigin"}
CSP_FRAME_ANCESTORS = ("frame-ancestors", "'none'", "'self'")


async def scan_clickjacking(
    client: RateLimitedClient,
    config: AuditConfig,
    log: AuditLogger,
) -> list[Finding]:
    findings: list[Finding] = []
    paths = config.resolve_clickjacking_paths()

    for path in paths:
        ex = await client.get(path)
        xfo = ex.response_headers.get("x-frame-options", "").lower()
        csp = ex.response_headers.get("content-security-policy", "").lower()

        if not xfo and "frame-ancestors" not in csp:
            findings.append(
                Finding(
                    test_id="clickjacking_missing",
                    title="Missing clickjacking protection",
                    severity=Severity.MEDIUM,
                    description=f"No X-Frame-Options or CSP frame-ancestors on {path}.",
                    evidence=f"headers={list(ex.response_headers.keys())[:15]}",
                    recommendation="Set X-Frame-Options: DENY or CSP frame-ancestors 'none'.",
                    exchange=ex,
                )
            )
        elif xfo and xfo not in PROTECTED_VALUES:
            findings.append(
                Finding(
                    test_id="clickjacking_weak",
                    title="Weak X-Frame-Options value",
                    severity=Severity.LOW,
                    description=f"Invalid X-Frame-Options: {xfo}",
                    evidence=xfo,
                    recommendation="Use DENY or SAMEORIGIN only.",
                    exchange=ex,
                )
            )

    if not findings:
        findings.append(
            Finding(
                test_id="clickjacking_ok",
                title="Clickjacking headers present",
                severity=Severity.INFO,
                description="X-Frame-Options or CSP frame-ancestors detected.",
                evidence=f"Paths checked: {paths}",
                recommendation="Ensure headers on all HTML responses.",
            )
        )
    return findings
