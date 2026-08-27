from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tools.security_audit.config import AuditConfig
from tools.security_audit.logger import AuditLogger
from tools.security_audit.models import AuditReport, Finding, HttpExchange, Severity, utc_now_iso
from tools.security_audit.reporter import write_all
from tools.security_audit.scanners import SCANNERS, run_scanners
from tools.security_audit.scanners.user_enum import scan_user_enumeration


def test_scanners_registry_has_eight_ids() -> None:
    assert set(SCANNERS.keys()) == {
        "rate_limit",
        "cors",
        "pii",
        "jwt",
        "user_enum",
        "clickjacking",
        "sqli",
        "idor",
    }


def test_audit_config_from_gymsite_file() -> None:
    cfg_path = Path("tools/security_audit/audit-config.gymsite.json")
    config = AuditConfig.from_file(cfg_path)
    assert config.targets == ["https://api.getgymsite.com.br"]
    assert config.auth_mode == "api"
    assert config.resolve_cors_probe_path() == "/health"
    path, method = config.resolve_rate_limit_probe()
    assert path == "/health"
    assert method == "GET"
    assert "/api/relatorios/{id}" in config.idor_paths
    assert config.resolve_admin_probe_paths() == [
        "/api/prospeccao/oportunidades",
        "/api/admin/llm-config",
    ]


@pytest.mark.asyncio
async def test_user_enum_skips_in_api_auth_mode() -> None:
    config = AuditConfig(targets=["https://api.example.com"], auth_mode="api")
    client = MagicMock()
    log = AuditLogger(verbose=False)
    findings = await scan_user_enumeration(client, config, log)
    assert len(findings) == 1
    assert findings[0].test_id == "user_enum_skip"
    assert findings[0].severity == Severity.INFO


@pytest.mark.asyncio
async def test_run_scanners_unknown_test_skipped() -> None:
    config = AuditConfig(targets=["https://api.example.com"])
    client = MagicMock()
    log = AuditLogger(verbose=False)

    async def fake_cors(*_args: object, **_kwargs: object) -> list[Finding]:
        return [
            Finding(
                test_id="cors_ok",
                title="ok",
                severity=Severity.INFO,
                description="",
                evidence="",
                recommendation="",
            )
        ]

    with patch.dict(SCANNERS, {"cors": fake_cors}, clear=False):
        findings, stopped, reason = await run_scanners(client, config, log, ["cors", "nope"], False)

    assert not stopped
    assert reason is None
    assert len(findings) == 1


def test_write_all_generates_json(tmp_path: Path) -> None:
    report = AuditReport(
        target="https://api.getgymsite.com.br",
        started_at=utc_now_iso(),
        finished_at=utc_now_iso(),
        findings=[
            Finding(
                test_id="cors_ok",
                title="CORS ok",
                severity=Severity.INFO,
                description="test",
                evidence="ev",
                recommendation="none",
            )
        ],
        tests_run=["cors"],
    )
    out = tmp_path / "report"
    paths = write_all(report, out)
    assert paths["json"].exists()
    assert "cors_ok" in paths["json"].read_text(encoding="utf-8")
    assert paths["html"].exists()
    assert paths["csv"].exists()


@pytest.mark.asyncio
async def test_rate_limit_skips_on_404() -> None:
    from tools.security_audit.scanners.rate_limit import scan_rate_limiting

    config = AuditConfig(
        targets=["https://api.example.com"],
        rate_limit_probe_path="/missing",
        rate_limit_probe_method="GET",
        brute_force_attempts=10,
    )
    client = MagicMock()
    client.get = AsyncMock(
        return_value=HttpExchange(
            method="GET",
            url="https://api.example.com/missing",
            status_code=404,
            response_body="not found",
        )
    )
    log = AuditLogger(verbose=False)
    findings = await scan_rate_limiting(client, config, log)
    assert any(f.test_id == "rate_limiting_skip" for f in findings)
    assert not any(f.test_id == "rate_limiting_missing" for f in findings)
