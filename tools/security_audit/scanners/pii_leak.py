from __future__ import annotations

import re

from tools.security_audit.config import AuditConfig
from tools.security_audit.http_client import RateLimitedClient
from tools.security_audit.logger import AuditLogger
from tools.security_audit.models import Finding, Severity

SENSITIVE_PATTERNS: list[tuple[str, re.Pattern[str], Severity]] = [
    ("password_field", re.compile(r'"password"\s*:\s*"[^"]{3,}"', re.I), Severity.CRITICAL),
    ("bcrypt_hash", re.compile(r"\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}", re.I), Severity.CRITICAL),
    ("sha256_hex", re.compile(r"\b[a-f0-9]{64}\b", re.I), Severity.HIGH),
    ("md5_hex", re.compile(r"\b[a-f0-9]{32}\b", re.I), Severity.MEDIUM),
    ("api_key", re.compile(r"(api[_-]?key|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}", re.I), Severity.CRITICAL),
    ("cpf", re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), Severity.HIGH),
    ("credit_card", re.compile(r"\b(?:\d[ -]*?){13,16}\b"), Severity.CRITICAL),
    ("email_bulk", re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), Severity.LOW),
]


async def scan_pii_leak(
    client: RateLimitedClient,
    config: AuditConfig,
    log: AuditLogger,
) -> list[Finding]:
    findings: list[Finding] = []
    headers = config.auth_headers()

    for path in config.profile_paths:
        log.debug(f"PII scan: {path}")
        ex = await client.get(path, headers=headers)
        if ex.status_code is None or ex.status_code >= 500:
            continue
        body = ex.response_body or ""
        for name, pattern, sev in SENSITIVE_PATTERNS:
            m = pattern.search(body)
            if m:
                snippet = m.group(0)[:120]
                findings.append(
                    Finding(
                        test_id="pii_leak",
                        title=f"Sensitive data pattern: {name}",
                        severity=sev,
                        description=f"Pattern '{name}' in response from {path}.",
                        evidence=f"Match: {snippet}",
                        recommendation="Return least privilege fields; never expose password hashes or secrets.",
                        exchange=ex,
                        metadata={"path": path, "pattern": name},
                    )
                )
                break

    if not findings:
        findings.append(
            Finding(
                test_id="pii_ok",
                title="No sensitive patterns on profile endpoints",
                severity=Severity.INFO,
                description="Scanned configured authenticated paths.",
                evidence=f"Paths: {config.profile_paths}",
                recommendation="Extend path list for full API map.",
            )
        )
    return findings
