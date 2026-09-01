from tools.log_redaction import redact_sensitive_text


def test_redact_bearer():
    raw = "auth failed Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig"
    assert "[REDACTED]" in redact_sensitive_text(raw)
    assert "eyJhbGci" not in redact_sensitive_text(raw)


def test_redact_x_access_token_header():
    token = "8845b104-4536-444e-98d6-03b7319cbf08"
    raw = f"poll failed X-Access-Token: {token}"
    out = redact_sensitive_text(raw)
    assert token not in out
    assert "X-Access-Token" in out
    assert "[REDACTED]" in out


def test_redact_access_token_kv():
    token = "8845b104-4536-444e-98d6-03b7319cbf08"
    raw = f"debug access_token={token}"
    out = redact_sensitive_text(raw)
    assert token not in out
    assert "access_token=" in out


def test_redact_jwt_standalone():
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.sig"
    out = redact_sensitive_text(f"token leaked {jwt}")
    assert jwt not in out
    assert "[REDACTED_JWT]" in out
