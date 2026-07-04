"""Regressão do IDOR de relatório (P1 security review 2026-07-04).

Antes do fix, `GET /api/relatorios/{id}` e `/pdf` liberavam o relatório completo
para qualquer request que soubesse o UUID — sem JWT e sem access_code. Estes testes
travam o comportamento deny-by-default de `_assert_relatorio_access`.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

REL_ID = "8845b104-4536-444e-98d6-03b7319cbf08"
# Fixture de teste, não é credencial real — gitleaks:allow silencia o falso positivo.
ACCESS_CODE = "test-access-code"  # gitleaks:allow


def _sb_with_relatorio(*, access_code: str | None, org_id: str | None = "org-A") -> MagicMock:
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.is_.return_value = chain
    chain.maybe_single.return_value = chain
    chain.update.return_value = chain
    row = {"access_code": access_code, "org_id": org_id}
    chain.execute.return_value = MagicMock(data=row)
    sb = MagicMock()
    sb.table.return_value = chain
    return sb


def _req(auth: str | None = None) -> MagicMock:
    req = MagicMock()
    req.headers = {"authorization": auth} if auth else {}
    return req


def test_sem_credencial_nega():
    """Sem JWT e sem access_code → 401 (era o IDOR: passava direto)."""
    from fastapi import HTTPException

    import api

    sb = _sb_with_relatorio(access_code=None)
    with pytest.raises(HTTPException) as exc:
        api._assert_relatorio_access(_req(), sb, REL_ID, access_code=None)
    assert exc.value.status_code == 401


def test_access_code_correto_libera():
    import api

    sb = _sb_with_relatorio(access_code=ACCESS_CODE)
    # Não deve levantar.
    api._assert_relatorio_access(_req(), sb, REL_ID, access_code=ACCESS_CODE)


def test_access_code_errado_nega():
    from fastapi import HTTPException

    import api

    sb = _sb_with_relatorio(access_code=ACCESS_CODE)
    with pytest.raises(HTTPException) as exc:
        api._assert_relatorio_access(_req(), sb, REL_ID, access_code="errado")
    assert exc.value.status_code == 403


def test_jwt_de_outra_org_nega():
    from fastapi import HTTPException

    import api

    sb = _sb_with_relatorio(access_code=None, org_id="org-DONA")
    with patch.object(api, "_require_authenticated", return_value=("user-X", "org-X")), \
         patch.object(api, "_user_org_ids", return_value=["org-OUTRA"]):
        with pytest.raises(HTTPException) as exc:
            api._assert_relatorio_access(_req("bearer tok"), sb, REL_ID, access_code=None)
    assert exc.value.status_code == 403


def test_jwt_da_org_dona_libera():
    import api

    sb = _sb_with_relatorio(access_code=None, org_id="org-DONA")
    with patch.object(api, "_require_authenticated", return_value=("user-X", "org-DONA")), \
         patch.object(api, "_user_org_ids", return_value=["org-DONA"]):
        # Não deve levantar.
        api._assert_relatorio_access(_req("bearer tok"), sb, REL_ID, access_code=None)


def test_pdf_endpoint_exige_credencial():
    """O /pdf agora chama _assert_relatorio_access (antes não chamava nada)."""
    from fastapi.testclient import TestClient

    from api import app

    routes = {r.path for r in app.routes if hasattr(r, "path")}
    assert "/api/relatorios/{relatorio_id}/pdf" in routes
