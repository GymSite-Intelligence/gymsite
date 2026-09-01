"""Guard: CHROMIUM_EXECUTABLE_PATH setado mas ausente deve falhar alto (não cair no bundle inexistente)."""
import pytest

from tools.playwright_chromium import chromium_launch_kwargs


def test_missing_executable_path_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("CHROMIUM_EXECUTABLE_PATH", str(tmp_path / "nope-chromium"))
    with pytest.raises(FileNotFoundError):
        chromium_launch_kwargs()


def test_existing_executable_path_used(monkeypatch, tmp_path):
    exe = tmp_path / "chromium"
    exe.write_text("#!/bin/sh\n")
    monkeypatch.setenv("CHROMIUM_EXECUTABLE_PATH", str(exe))
    assert chromium_launch_kwargs()["executable_path"] == str(exe)


def test_no_env_no_executable(monkeypatch):
    monkeypatch.delenv("CHROMIUM_EXECUTABLE_PATH", raising=False)
    assert "executable_path" not in chromium_launch_kwargs()
