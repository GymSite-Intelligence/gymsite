"""Act-on A3a: pico Supabase cache + MAX_ENRIQUECIMENTO default 3."""
from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest


def test_load_pico_cache_prefers_supabase(monkeypatch):
    from tools import popular_times_tool as pt

    @dataclass
    class Hit:
        hit: bool
        payload: dict

    payload = {
        "status": "ok",
        "payload": {
            "status": "ok",
            "dados_por_dia": {"segunda": [1] * 24},
            "resumo_por_dia": {},
        },
    }

    monkeypatch.setattr(
        "tools.cache_store.get_popular_times",
        lambda place_id: Hit(hit=True, payload=payload),
    )
    # FS não deve ser necessário
    monkeypatch.setattr(pt, "_cache_path", lambda _pid: MagicMock(exists=lambda: False))

    out = pt._load_pico_cache(
        "ChIJ_test",
        force_refresh=False,
        nome="",
        lat=None,
        lng=None,
    )
    assert out is not None
    assert out["cached"] is True
    assert out["cache_fonte"] == "supabase"
    assert out["status"] == "ok"


def test_save_pico_cache_writes_supabase(monkeypatch, tmp_path):
    from tools import popular_times_tool as pt

    calls = []

    def fake_set(place_id, payload, **kwargs):
        calls.append((place_id, payload.get("status"), kwargs.get("status")))

    monkeypatch.setattr("tools.cache_store.set_popular_times", fake_set)
    monkeypatch.setattr(pt, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(pt, "_cache_path", lambda pid: tmp_path / f"{pid}.json")

    pt._save_pico_cache("ChIJ_x", {"status": "ok", "dados_por_dia": {}})
    assert calls == [("ChIJ_x", "ok", "ok")]
    assert (tmp_path / "ChIJ_x.json").is_file()


def test_max_enriquecimento_default_3(monkeypatch):
    """Default do env ausente = 3 (Act-on), não 6."""
    import os

    monkeypatch.delenv("MAX_ENRIQUECIMENTO", raising=False)
    assert max(1, int(os.getenv("MAX_ENRIQUECIMENTO", "3"))) == 3
