"""Redact sensitive tokens from log messages before JSON export."""
from __future__ import annotations

import re

_BEARER = re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", re.I)
_JWT = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
_HEADER_OR_KEY_TOKEN = re.compile(
    r"(?i)((?:x-access-token|access_token|x-site-chat-token)[\s\"'=:]+\s*[\"']?)"
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
)
_KV_ACCESS_TOKEN = re.compile(
    r"(?i)(access_token\s*[=:]\s*[\"']?)([0-9a-f-]{36})"
)


def redact_sensitive_text(text: str) -> str:
    if not text:
        return text
    out = _BEARER.sub(r"\1[REDACTED]", text)
    out = _JWT.sub("[REDACTED_JWT]", out)
    out = _HEADER_OR_KEY_TOKEN.sub(r"\1[REDACTED]", out)
    out = _KV_ACCESS_TOKEN.sub(r"\1[REDACTED]", out)
    return out
