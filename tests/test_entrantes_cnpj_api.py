"""Rotas manuais de entrantes CNPJ (validação + enriquecimento)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

REL_ID = "8845b104-4536-444e-98d6-03b7319cbf08"
CNPJ = "12345678000199"


def _mock_supabase_block(*, entrantes: list[dict] | None = None) -> MagicMock:
    block = {"entrantes": entrantes or [{"cnpj": CNPJ, "razao_social": "Academia Teste LTDA"}]}
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.maybe_single.return_value = chain
    chain.execute.return_value = MagicMock(data={"entrantes_cnpj_90d": block})
    chain.update.return_value = chain

    sb = MagicMock()
    sb.table.return_value = chain
    return sb


@pytest.fixture
def client():
    from api import app

    return TestClient(app)


def test_post_enriquecer_route_registered(client: TestClient):
    routes = {(r.path, tuple(r.methods)) for r in client.app.routes if hasattr(r, "methods")}
    assert (
        "/api/relatorios/{relatorio_id}/entrantes-cnpj/enriquecer",
        ("POST",),
    ) in routes


@patch("api._supabase_client")
@patch("tools.cnpj_enrichment.enriquecer_entrante_unico")
def test_post_enriquecer_ok(mock_enrich, mock_sb_fn, client: TestClient):
    mock_sb_fn.return_value = _mock_supabase_block()
    mock_enrich.return_value = (
        {"cnpj": CNPJ, "email_empresa": "a@b.com"},
        {"receita_calls": 1},
    )

    res = client.post(
        f"/api/relatorios/{REL_ID}/entrantes-cnpj/enriquecer",
        json={"cnpj": CNPJ, "usar_apollo": False},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["cnpj"] == CNPJ
    mock_enrich.assert_called_once()


@patch("api._supabase_client")
def test_post_enriquecer_404_sem_block(mock_sb_fn, client: TestClient):
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.maybe_single.return_value = chain
    chain.execute.return_value = MagicMock(data=None)
    mock_sb_fn.return_value = MagicMock(table=MagicMock(return_value=chain))

    res = client.post(
        f"/api/relatorios/{REL_ID}/entrantes-cnpj/enriquecer",
        json={"cnpj": CNPJ},
    )
    assert res.status_code == 404
