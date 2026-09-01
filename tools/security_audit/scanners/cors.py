from __future__ import annotations

from tools.security_audit.config import AuditConfig
from tools.security_audit.http_client import RateLimitedClient
from tools.security_audit.logger import AuditLogger
from tools.security_audit.models import Finding, Severity


def _classify_cors(origin: str, acao: str | None, credentials: str | None) -> Severity:
    if not acao:
        return Severity.INFO
    if acao == "*" and credentials and credentials.lower() == "true":
        return Severity.CRITICAL
    if acao == origin and origin not in ("null", ""):
        if "evil" in origin or "attacker" in origin:
            return Severity.CRITICAL
        return Severity.HIGH
    if acao == "*":
        return Severity.MEDIUM
    return Severity.INFO


async def scan_cors(
    client: RateLimitedClient,
    config: AuditConfig,
    log: AuditLogger,
) -> list[Finding]:
    findings: list[Finding] = []
    path = config.resolve_cors_probe_path()

    for origin in config.cors_origins:
        log.debug(f"CORS probe origin={origin}")
        ex = await client.options(
            path,
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, Authorization",
            },
        )
        acao = ex.response_headers.get("access-control-allow-origin")
        acac = ex.response_headers.get("access-control-allow-credentials")
        if acao:
            sev = _classify_cors(origin, acao, acac)
            if sev != Severity.INFO:
                findings.append(
                    Finding(
                        test_id="cors_reflection",
                        title="CORS misconfiguration",
                        severity=sev,
                        description=f"Origin '{origin}' reflected or wildcard with credentials.",
                        evidence=f"ACAO={acao} ACAC={acac} status={ex.status_code}",
                        recommendation="Allowlist trusted origins; never reflect arbitrary Origin with credentials.",
                        exchange=ex,
                        metadata={"origin": origin},
                    )
                )

        ex_get = await client.get(path, headers={"Origin": origin})
        acao_get = ex_get.response_headers.get("access-control-allow-origin")
        if acao_get == origin and origin not in ("null", ""):
            findings.append(
                Finding(
                    test_id="cors_get_reflection",
                    title="CORS reflected on GET",
                    severity=Severity.HIGH,
                    description="Simple request reflects malicious Origin.",
                    evidence=f"GET ACAO={acao_get} for Origin={origin}",
                    recommendation="Validate Origin against static allowlist on all methods.",
                    exchange=ex_get,
                )
            )

    if not findings:
        findings.append(
            Finding(
                test_id="cors_ok",
                title="No obvious CORS reflection",
                severity=Severity.INFO,
                description="Tested malicious origins; no unsafe ACAO observed.",
                evidence=f"Origins tested: {config.cors_origins}",
                recommendation="Keep allowlist enforced; retest after API changes.",
            )
        )
    return findings
