from __future__ import annotations

import statistics

from tools.security_audit.config import AuditConfig
from tools.security_audit.http_client import RateLimitedClient
from tools.security_audit.logger import AuditLogger
from tools.security_audit.models import Finding, Severity


async def scan_rate_limiting(
    client: RateLimitedClient,
    config: AuditConfig,
    log: AuditLogger,
) -> list[Finding]:
    findings: list[Finding] = []
    attempts = min(config.brute_force_attempts, 120)
    milestones = {10, 50, 100}
    latencies: list[float] = []
    statuses: list[int | None] = []
    rate_headers_seen = False
    blocked = False
    path, method = config.resolve_rate_limit_probe()
    path_missing = False

    payload = {"email": config.missing_email, "password": "invalid-password-audit"}
    log.info(f"Rate limit test: {attempts} {method} requests to {path}")

    for i in range(1, attempts + 1):
        if method == "GET":
            ex = await client.get(path)
        else:
            ex = await client.post(
                path,
                headers={"Content-Type": "application/json"},
                json_body=payload,
            )
        if ex.status_code == 404:
            path_missing = True
            break
        if ex.elapsed_ms:
            latencies.append(ex.elapsed_ms)
        statuses.append(ex.status_code)
        rh = {k.lower(): v for k, v in ex.response_headers.items()}
        if any(k.startswith("x-ratelimit") for k in rh):
            rate_headers_seen = True
        if ex.status_code in (429, 403):
            blocked = True
            if i in milestones:
                findings.append(
                    Finding(
                        test_id="rate_limiting_block",
                        title="Rate limiting triggered",
                        severity=Severity.INFO,
                        description=f"HTTP {ex.status_code} after {i} attempts.",
                        evidence=f"Status {ex.status_code} at attempt {i}; elapsed {ex.elapsed_ms:.0f}ms",
                        recommendation="Document limit for operators; ensure consistent error body.",
                        exchange=ex,
                        metadata={"attempt": i},
                    )
                )
            break

    if path_missing:
        findings.append(
            Finding(
                test_id="rate_limiting_skip",
                title="Rate limit probe path not found",
                severity=Severity.INFO,
                description=f"{method} {path} returned 404; burst skipped.",
                evidence=f"path={path} method={method}",
                recommendation="Set rate_limit_probe_path to an existing public route (e.g. /health).",
            )
        )
        return findings

    if not blocked and attempts >= 50:
        findings.append(
            Finding(
                test_id="rate_limiting_missing",
                title="No rate limiting detected on probe",
                severity=Severity.HIGH,
                description=f"{attempts} consecutive requests without 429/403 on {path}.",
                evidence=f"Last statuses sample: {statuses[-5:]}",
                recommendation="Add IP + account rate limits; return 429 with Retry-After.",
            )
        )

    if not rate_headers_seen:
        findings.append(
            Finding(
                test_id="rate_limiting_headers",
                title="Rate limit headers absent",
                severity=Severity.MEDIUM,
                description="X-RateLimit-* headers not observed during burst.",
                evidence="No X-RateLimit-Limit / Remaining in responses.",
                recommendation="Expose X-RateLimit-Limit, Remaining, Reset for API clients.",
            )
        )
    else:
        findings.append(
            Finding(
                test_id="rate_limiting_headers_ok",
                title="Rate limit headers present",
                severity=Severity.INFO,
                description="X-RateLimit headers detected.",
                evidence="Headers present in at least one response.",
                recommendation="None.",
            )
        )

    for m in sorted(milestones):
        if len(latencies) >= m:
            sample = latencies[:m]
            findings.append(
                Finding(
                    test_id="rate_limiting_timing",
                    title=f"Probe latency at {m} requests",
                    severity=Severity.INFO,
                    description="Timing snapshot for burst simulation.",
                    evidence=f"p50={statistics.median(sample):.0f}ms max={max(sample):.0f}ms",
                    recommendation="Monitor latency degradation under load.",
                    metadata={"attempts": m},
                )
            )

    return findings
