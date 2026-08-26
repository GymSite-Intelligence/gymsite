from __future__ import annotations

import time
from typing import Any

from tools.security_audit.config import AuditConfig
from tools.security_audit.http_client import RateLimitedClient
from tools.security_audit.logger import AuditLogger
from tools.security_audit.models import Finding, Severity

SQL_ERROR_MARKERS = (
    "sql syntax",
    "mysql",
    "postgresql",
    "sqlite",
    "ora-",
    "unclosed quotation",
    "syntax error",
    "odbc",
    "jdbc",
)

SQLI_PAYLOADS = [
    "' OR '1'='1",
    "' UNION SELECT NULL--",
    "admin'--",
    "1' AND SLEEP(3)--",
    "1; WAITFOR DELAY '0:0:3'--",
]


def _render_body(template: dict[str, Any], payload: str, param: str) -> dict[str, Any]:
    body: dict[str, Any] = {}
    for key, value in template.items():
        if isinstance(value, str):
            body[key] = value.replace("{payload}", payload) if key == param or "{payload}" in value else value
        else:
            body[key] = value
    body[param] = payload
    return body


async def scan_sqli(
    client: RateLimitedClient,
    config: AuditConfig,
    log: AuditLogger,
) -> list[Finding]:
    findings: list[Finding] = []
    endpoints = config.resolve_sqli_endpoints()

    for endpoint in endpoints:
        path = str(endpoint["path"])
        method = str(endpoint.get("method", "GET")).upper()
        body_template = endpoint.get("body")
        if isinstance(body_template, dict):
            body_template = dict(body_template)

        for param in config.sqli_param_names:
            for payload in SQLI_PAYLOADS:
                if method == "POST" and body_template:
                    body = _render_body(body_template, payload, param)
                    t0 = time.perf_counter()
                    ex = await client.post(path, headers={"Content-Type": "application/json"}, json_body=body)
                    elapsed = (time.perf_counter() - t0) * 1000
                else:
                    t0 = time.perf_counter()
                    ex = await client.get(path, params={param: payload})
                    elapsed = (time.perf_counter() - t0) * 1000

                if ex.status_code == 404:
                    continue

                body_text = (ex.response_body or "").lower()
                if any(marker in body_text for marker in SQL_ERROR_MARKERS):
                    findings.append(
                        Finding(
                            test_id="sqli_error_based",
                            title="SQL injection (error-based)",
                            severity=Severity.CRITICAL,
                            description=f"SQL error leaked on {path} param={param}.",
                            evidence=f"payload={payload} body_snippet={body_text[:300]}",
                            recommendation="Use parameterized queries; stop immediately and patch.",
                            exchange=ex,
                            metadata={"param": param, "payload": payload},
                        )
                    )
                    return findings

                if "sleep" in payload.lower() or "waitfor" in payload.lower():
                    if elapsed > 2800:
                        findings.append(
                            Finding(
                                test_id="sqli_time_based",
                                title="SQL injection (time-based)",
                                severity=Severity.CRITICAL,
                                description=f"Delayed response ({elapsed:.0f}ms) on {path}.",
                                evidence=f"payload={payload} param={param}",
                                recommendation="Parameterized queries; WAF review.",
                                exchange=ex,
                                metadata={"elapsed_ms": elapsed},
                            )
                        )
                        return findings

    findings.append(
        Finding(
            test_id="sqli_none",
            title="No SQLi indicators in sampled inputs",
            severity=Severity.INFO,
            description="Error/time-based probes did not trigger.",
            evidence=f"Endpoints: {len(endpoints)} payloads: {len(SQLI_PAYLOADS)}",
            recommendation="Expand endpoint map; manual review for 2nd-order SQLi.",
        )
    )
    return findings
