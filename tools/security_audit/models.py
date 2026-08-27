from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


OWASP_MAP: dict[str, str] = {
    "rate_limiting": "A07:2021 – Identification and Authentication Failures",
    "cors": "A05:2021 – Security Misconfiguration",
    "pii_leak": "A01:2021 – Broken Access Control",
    "jwt": "A07:2021 – Identification and Authentication Failures",
    "user_enumeration": "A07:2021 – Identification and Authentication Failures",
    "clickjacking": "A05:2021 – Security Misconfiguration",
    "sqli": "A03:2021 – Injection",
    "idor": "A01:2021 – Broken Access Control",
}


CVSS_DEFAULT: dict[Severity, float] = {
    Severity.CRITICAL: 9.8,
    Severity.HIGH: 7.5,
    Severity.MEDIUM: 5.3,
    Severity.LOW: 3.1,
    Severity.INFO: 0.0,
}


@dataclass
class HttpExchange:
    method: str
    url: str
    request_headers: dict[str, str] = field(default_factory=dict)
    request_body: str | None = None
    status_code: int | None = None
    response_headers: dict[str, str] = field(default_factory=dict)
    response_body: str | None = None
    elapsed_ms: float | None = None


@dataclass
class Finding:
    test_id: str
    title: str
    severity: Severity
    description: str
    evidence: str
    recommendation: str
    owasp: str = ""
    cvss: float = 0.0
    exchange: HttpExchange | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.owasp:
            self.owasp = OWASP_MAP.get(self.test_id.split("_")[0], "Unmapped")
        if self.cvss == 0.0 and self.severity != Severity.INFO:
            self.cvss = CVSS_DEFAULT.get(self.severity, 0.0)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["severity"] = self.severity.value
        if self.exchange:
            payload["exchange"] = asdict(self.exchange)
        return payload


@dataclass
class AuditReport:
    target: str
    started_at: str
    finished_at: str
    findings: list[Finding] = field(default_factory=list)
    stopped_early: bool = False
    stop_reason: str | None = None
    tests_run: list[str] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        out = {s.value: 0 for s in Severity}
        for f in self.findings:
            out[f.severity.value] += 1
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "stopped_early": self.stopped_early,
            "stop_reason": self.stop_reason,
            "tests_run": self.tests_run,
            "summary": self.counts,
            "findings": [f.to_dict() for f in self.findings],
        }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
