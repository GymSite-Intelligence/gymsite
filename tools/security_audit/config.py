from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AuditConfig:
    """Centralized audit configuration."""

    targets: list[str]
    token: str | None = None
    api_key: str | None = None
    api_key_header: str = "X-API-Key"
    user_a_token: str | None = None
    user_b_token: str | None = None
    proxy: str | None = None
    verify_ssl: bool = True
    timeout_sec: float = 15.0
    internal_rate_limit_rps: float = 5.0
    auth_mode: str = "api"
    supabase_auth_url: str | None = None
    login_path: str = "/auth/login"
    logout_path: str = "/auth/logout"
    register_path: str = "/auth/register"
    forgot_password_path: str = "/auth/forgot-password"
    cors_probe_path: str | None = None
    rate_limit_probe_path: str | None = None
    rate_limit_probe_method: str = "POST"
    clickjacking_paths: list[str] = field(default_factory=list)
    admin_probe_paths: list[str] = field(default_factory=list)
    sqli_endpoints: list[dict[str, Any]] = field(default_factory=list)
    profile_paths: list[str] = field(
        default_factory=lambda: [
            "/users/me",
            "/profile",
            "/account",
            "/settings",
            "/admin",
        ]
    )
    idor_paths: list[str] = field(
        default_factory=lambda: [
            "/users/{id}",
            "/accounts/{id}",
            "/orders/{id}",
        ]
    )
    sqli_param_names: list[str] = field(
        default_factory=lambda: ["q", "search", "email", "username", "id", "sort", "filter"]
    )
    existing_email: str = "existing@example.com"
    missing_email: str = "missing-not-found@example.com"
    existing_password: str = "WrongPassword123!"
    user_a_id: str = "1"
    user_b_id: str = "2"
    extra_headers: dict[str, str] = field(default_factory=dict)
    webhook_url: str | None = None
    critical_stop: bool = True
    brute_force_attempts: int = 100
    cors_origins: list[str] = field(
        default_factory=lambda: [
            "https://evil.com",
            "https://attacker.com",
            "null",
            "https://sub.evil.example",
        ]
    )

    @classmethod
    def from_file(cls, path: Path) -> AuditConfig:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        targets = data.pop("targets", data.pop("target", None))
        if isinstance(targets, str):
            targets = [targets]
        if not targets:
            raise ValueError("Config must include 'targets' or 'target'")
        return cls(targets=targets, **{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def auth_headers(self, token: str | None = None) -> dict[str, str]:
        headers = dict(self.extra_headers)
        bearer = token or self.token
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"
        if self.api_key:
            headers[self.api_key_header] = self.api_key
        return headers

    def resolve_cors_probe_path(self) -> str:
        return self.cors_probe_path or self.login_path

    def resolve_rate_limit_probe(self) -> tuple[str, str]:
        path = self.rate_limit_probe_path or self.login_path
        method = (self.rate_limit_probe_method or "POST").upper()
        return path, method

    def resolve_clickjacking_paths(self) -> list[str]:
        if self.clickjacking_paths:
            return self.clickjacking_paths
        return ["/", self.login_path]

    def resolve_jwt_probe_path(self) -> str:
        return self.profile_paths[0] if self.profile_paths else "/users/me"

    def resolve_sqli_endpoints(self) -> list[dict[str, Any]]:
        if self.sqli_endpoints:
            return self.sqli_endpoints
        return [
            {"path": self.login_path, "method": "POST", "body": {"email": "{payload}", "password": "x"}},
            {"path": "/search", "method": "GET"},
        ]

    def resolve_admin_probe_paths(self) -> list[str]:
        if self.admin_probe_paths:
            return self.admin_probe_paths
        return ["/admin", "/admin/users", "/api/admin/stats"]
