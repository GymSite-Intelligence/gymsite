"""P2 capability token masking in tools/sanitize."""
from __future__ import annotations

from tools.sanitize import (
    mask_capability_token,
    safe_headers,
    safe_query_params,
    safe_span_attribute,
)

# Fixture de teste, não é credencial real — gitleaks:allow silencia falso positivo.
TEST_CAPABILITY_TOKEN = "00000000-0000-4000-8000-000000000099"  # gitleaks:allow


def test_mask_capability_token_last_four():
    raw = TEST_CAPABILITY_TOKEN
    masked = mask_capability_token(raw)
    assert masked is not None
    assert masked.endswith("0099")
    assert raw[:8] not in masked
    assert mask_capability_token("abc") == "****"
    assert mask_capability_token(None) is None


def test_safe_headers_masks_x_access_token():
    out = safe_headers({"X-Access-Token": TEST_CAPABILITY_TOKEN, "Accept": "json"})
    assert out["Accept"] == "json"
    assert out["X-Access-Token"].endswith("0099")
    assert "00000000" not in out["X-Access-Token"]


def test_safe_headers_redacts_authorization():
    out = safe_headers({"Authorization": "Bearer secret-jwt"})
    assert out["Authorization"] == "[REDACTED]"


def test_safe_query_params_masks_access_code():
    out = safe_query_params({"access_code": TEST_CAPABILITY_TOKEN, "foo": "bar"})
    assert out["foo"] == "bar"
    assert out["access_code"].endswith("0099")


def test_safe_span_attribute_masks_access_token():
    attr = safe_span_attribute("access_token", TEST_CAPABILITY_TOKEN)
    assert attr is not None
    name, val = attr
    assert name == "access_token_masked"
    assert val.endswith("0099")
