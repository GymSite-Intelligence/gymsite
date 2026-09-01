from __future__ import annotations

from tools.security_audit.config import AuditConfig
from tools.security_audit.http_client import RateLimitedClient
from tools.security_audit.logger import AuditLogger
from tools.security_audit.models import Finding
from tools.security_audit.scanners.clickjacking import scan_clickjacking
from tools.security_audit.scanners.cors import scan_cors
from tools.security_audit.scanners.idor import scan_idor
from tools.security_audit.scanners.jwt import scan_jwt
from tools.security_audit.scanners.pii_leak import scan_pii_leak
from tools.security_audit.scanners.rate_limit import scan_rate_limiting
from tools.security_audit.scanners.sqli import scan_sqli
from tools.security_audit.scanners.user_enum import scan_user_enumeration

SCANNERS = {
    "rate_limit": scan_rate_limiting,
    "cors": scan_cors,
    "pii": scan_pii_leak,
    "jwt": scan_jwt,
    "user_enum": scan_user_enumeration,
    "clickjacking": scan_clickjacking,
    "sqli": scan_sqli,
    "idor": scan_idor,
}

CRITICAL_SCANNERS = {"sqli", "idor"}


async def run_scanners(
    client: RateLimitedClient,
    config: AuditConfig,
    log: AuditLogger,
    tests: list[str],
    critical_stop: bool,
) -> tuple[list[Finding], bool, str | None]:
    findings: list[Finding] = []
    for name in tests:
        fn = SCANNERS.get(name)
        if not fn:
            log.warning(f"Unknown test skipped: {name}")
            continue
        log.info(f"Running scanner: {name}")
        batch = await fn(client, config, log)
        findings.extend(batch)
        critical_hits = [f for f in batch if f.severity.value == "critical"]
        if critical_stop and name in CRITICAL_SCANNERS and critical_hits:
            reason = f"Critical finding in {name}: {critical_hits[0].title}"
            log.critical(f"STOP — {reason}")
            return findings, True, reason
    return findings, False, None
