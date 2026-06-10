from __future__ import annotations

from typing import Any, Dict, List

import types

import httpx

from tools.bcb_imobiliario_olinda import (
    extrair_resumo_imobiliario,
    fetch_mercado_imobiliario_series,
)


class _DummyResponse:
    def __init__(self, payload: Dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.headers = {"content-type": "application/json; charset=utf-8"}

    def json(self) -> Dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "erro",
                request=types.SimpleNamespace(url="http://test"),
                response=types.SimpleNamespace(status_code=self.status_code),
            )


def _build_sample_payload() -> Dict[str, Any]:
    # Simula payload mínimo de Olinda: value=[{Data, Info, Valor}, ...].
    return {
        "value": [
            {
                "Data": "2024-05-01T00:00:00",
                "Info": "Financiamento imobiliário residencial",
                "Valor": "12345,67",
            },
            {
                "Data": "2024-04-01T00:00:00",
                "Info": "Financiamento imobiliário residencial",
                "Valor": "12000,00",
            },
            {
                "Data": "2024-05-01T00:00:00",
                "Info": "Crédito direcionado imobiliário total",
                "Valor": "98765,43",
            },
        ]
    }


def test_fetch_mercado_imobiliario_series_basic(monkeypatch: Any) -> None:
    payload = _build_sample_payload()

    def fake_get(url: str, *, timeout: float) -> _DummyResponse:  # type: ignore[override]
        assert "MercadoImobiliario" in url
        assert "$format=json" in url
        return _DummyResponse(payload)

    monkeypatch.setattr(httpx, "get", fake_get)

    resp = fetch_mercado_imobiliario_series()
    assert resp["ok"] is True
    series: List[Dict[str, Any]] = resp["series"]
    # Duas séries distintas pelo campo Info.
    assert len(series) == 2
    infos = {s["info"] for s in series}
    assert "Financiamento imobiliário residencial" in infos
    assert "Crédito direcionado imobiliário total" in infos

    # Confere normalização básica de data/valor.
    fin = next(s for s in series if s["info"] == "Financiamento imobiliário residencial")
    assert fin["data"].startswith("2024-05")
    assert abs(fin["valor"] - 12345.67) < 0.01
    assert "filter=Info" in fin["url"]


def test_extrair_resumo_imobiliario_uses_fetch(monkeypatch: Any) -> None:
    payload = _build_sample_payload()

    def fake_get(url: str, *, timeout: float) -> _DummyResponse:  # type: ignore[override]
        return _DummyResponse(payload)

    monkeypatch.setattr(httpx, "get", fake_get)

    resumo = extrair_resumo_imobiliario(cidade_contexto="Hortolândia/SP")
    assert resumo["ok"] is True
    assert resumo["cidade_contexto"] == "Hortolândia/SP"
    assert resumo["series"]  # amostra não vazia
    assert "norte" in resumo and isinstance(resumo["norte"], str)
    # Pelo menos um destaque deve ser identificado para as strings de teste.
    destaques = resumo.get("destaques") or {}
    assert destaques


def test_fetch_mercado_imobiliario_series_http_error(monkeypatch: Any) -> None:
    def fake_get(url: str, *, timeout: float) -> _DummyResponse:  # type: ignore[override]
        return _DummyResponse({"value": []}, status_code=500)

    monkeypatch.setattr(httpx, "get", fake_get)

    resp = fetch_mercado_imobiliario_series()
    assert resp["ok"] is False
    assert "HTTP" in (resp.get("erro") or "")

