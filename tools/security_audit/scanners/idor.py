from __future__ import annotations

from tools.security_audit.config import AuditConfig
from tools.security_audit.http_client import RateLimitedClient
from tools.security_audit.logger import AuditLogger
from tools.security_audit.models import Finding, Severity


async def scan_idor(
    client: RateLimitedClient,
    config: AuditConfig,
    log: AuditLogger,
) -> list[Finding]:
    findings: list[Finding] = []
    token_a = config.user_a_token or config.token
    token_b = config.user_b_token

    if not token_a:
        return [
            Finding(
                test_id="idor_skip",
                title="IDOR tests skipped",
                severity=Severity.INFO,
                description="Provide --token or --user-a-token.",
                evidence="",
                recommendation="Supply two user tokens for horizontal escalation test.",
            )
        ]

    for template in config.idor_paths:
        path_a = template.replace("{id}", config.user_a_id)
        path_b = template.replace("{id}", config.user_b_id)

        ex_owner = await client.get(path_a, headers=config.auth_headers(token_a))
        if ex_owner.status_code not in (200, 201):
            log.debug(f"IDOR skip {path_a} status={ex_owner.status_code}")
            continue

        if token_b:
            ex_cross = await client.get(path_a, headers=config.auth_headers(token_b))
            if ex_cross.status_code == 200 and (ex_cross.response_body or "") == (ex_owner.response_body or ""):
                findings.append(
                    Finding(
                        test_id="idor_horizontal",
                        title="IDOR — horizontal privilege escalation",
                        severity=Severity.CRITICAL,
                        description=f"User B accessed User A resource at {path_a}.",
                        evidence=f"status={ex_cross.status_code} same_body={bool(ex_cross.response_body)}",
                        recommendation="Enforce ownership check on every object access.",
                        exchange=ex_cross,
                    )
                )
                return findings

        for seq_id in ("123", "124", "125"):
            seq_path = template.replace("{id}", seq_id)
            ex_seq = await client.get(seq_path, headers=config.auth_headers(token_a))
            if ex_seq.status_code == 200 and seq_id != config.user_a_id:
                findings.append(
                    Finding(
                        test_id="idor_sequential",
                        title="IDOR — predictable sequential ID",
                        severity=Severity.HIGH,
                        description=f"Accessible resource at {seq_path}.",
                        evidence=f"status=200 id={seq_id}",
                        recommendation="Use UUIDs + authorization middleware.",
                        exchange=ex_seq,
                    )
                )

    admin_paths = config.resolve_admin_probe_paths()
    for ap in admin_paths:
        ex = await client.get(ap, headers=config.auth_headers(token_a))
        if ex.status_code == 200:
            findings.append(
                Finding(
                    test_id="idor_vertical",
                    title="Potential vertical privilege escalation",
                    severity=Severity.CRITICAL,
                    description=f"Non-admin token accessed {ap}.",
                    evidence=f"status=200",
                    recommendation="Role-based access control on admin routes.",
                    exchange=ex,
                )
            )
            return findings

    if not any(f.severity == Severity.CRITICAL for f in findings):
        findings.append(
            Finding(
                test_id="idor_ok",
                title="No IDOR detected in configured probes",
                severity=Severity.INFO,
                description="Horizontal/vertical checks did not confirm access.",
                evidence=f"paths={config.idor_paths}",
                recommendation="Map all object IDs from OpenAPI spec.",
            )
        )
    return findings
