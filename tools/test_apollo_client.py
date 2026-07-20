"""Testes tools/apollo_client — upsert + sequence enrollment (httpx mock)."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _apollo_env(monkeypatch):
    monkeypatch.setenv("APOLLO_API_KEY", "test-key")
    monkeypatch.setenv("APOLLO_SYNC_ENABLED", "true")
    monkeypatch.setenv("APOLLO_SEQUENCE_ID", "seq-123")
    monkeypatch.setenv("APOLLO_EMAIL_ACCOUNT_ID", "email-acct-456")
    monkeypatch.delenv("APOLLO_BASE_URL", raising=False)


def test_sync_lead_creates_contact_and_enrolls_sequence():
    from tools import apollo_client

    mock_resp_contact = MagicMock()
    mock_resp_contact.status_code = 200
    mock_resp_contact.content = b'{"contact":{"id":"c-99"}}'
    mock_resp_contact.json.return_value = {"contact": {"id": "c-99"}}

    mock_resp_seq = MagicMock()
    mock_resp_seq.status_code = 200
    mock_resp_seq.content = b"{}"
    mock_resp_seq.text = ""

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.side_effect = [mock_resp_contact, mock_resp_seq]

    with patch("httpx.Client", return_value=mock_client):
        out = apollo_client.sync_lead_to_apollo(
            nome="Maria Silva",
            email="maria@example.com",
            cidade="Fortaleza",
            bairro="Coco",
            perfil="vou_abrir",
        )

    assert out["ok"] is True
    assert out["contact_id"] == "c-99"
    assert out["sequence_enrolled"] is True
    assert out["sequence_id"] == "seq-123"

    calls = mock_client.post.call_args_list
    assert calls[0][0][0].endswith("/api/v1/contacts")
    body = calls[0][1]["json"]
    assert body["run_dedupe"] is True
    assert "organization_name" not in body
    assert calls[1][0][0].endswith("/api/v1/emailer_campaigns/seq-123/add_contact_ids")


def test_sync_lead_skips_sequence_without_email_account(monkeypatch):
    from tools import apollo_client

    monkeypatch.delenv("APOLLO_EMAIL_ACCOUNT_ID", raising=False)

    mock_resp_contact = MagicMock()
    mock_resp_contact.status_code = 200
    mock_resp_contact.content = b'{"contact":{"id":"c-1"}}'
    mock_resp_contact.json.return_value = {"contact": {"id": "c-1"}}

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_resp_contact

    with patch("httpx.Client", return_value=mock_client):
        out = apollo_client.sync_lead_to_apollo(nome="Joao", email="j@ex.com")

    assert out["ok"] is True
    assert out["sequence_enrolled"] is False
    assert out["sequence_error"] == "sem APOLLO_EMAIL_ACCOUNT_ID"
    assert mock_client.post.call_count == 1


def test_default_base_url_is_api_v1():
    from tools.apollo_client import _DEFAULT_BASE

    assert _DEFAULT_BASE == "https://api.apollo.io/api/v1"
