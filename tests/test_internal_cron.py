"""Auth do endpoint cron weekly market batch."""
from __future__ import annotations

import os

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api import app
from backend.routers.internal_cron import _check_cron_secret


def test_check_cron_secret_missing_env(monkeypatch):
    monkeypatch.delenv("MARKET_BATCH_CRON_SECRET", raising=False)
    with pytest.raises(HTTPException) as exc:
        _check_cron_secret("x")
    assert exc.value.status_code == 503


def test_check_cron_secret_wrong(monkeypatch):
    monkeypatch.setenv("MARKET_BATCH_CRON_SECRET", "sekret")
    with pytest.raises(HTTPException) as exc:
        _check_cron_secret("wrong")
    assert exc.value.status_code == 401


def test_cron_endpoint_requires_secret(monkeypatch):
    monkeypatch.setenv("MARKET_BATCH_CRON_SECRET", "sekret")
    client = TestClient(app)
    r = client.post("/api/internal/cron/weekly-market-batch")
    assert r.status_code == 401
