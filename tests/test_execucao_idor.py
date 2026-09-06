"""Regressao IDOR em /api/execucao/playbooks/gerar (Opsera leftover).

Antes do fix, relatorio com user_id vazio/ausente pulava o check de ownership
e qualquer JWT autenticado podia gerar playbook.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


def _sb_relatorio(*, user_id):
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.is_.return_value = chain
    chain.maybe_single.return_value = chain
    chain.execute.return_value = MagicMock(
        data={"user_id": user_id, "org_id": None}
    )
    sb = MagicMock()
    sb.table.return_value = chain
    return sb


def test_execucao_gerar_owner_vazio_nega():
    from backend.routers import execucao
    from backend.routers.execucao import GerarPlaybookRequest

    req = MagicMock()
    with patch.object(execucao, "_require_user", return_value="user-A"), \
         patch.object(execucao, "_sb", return_value=_sb_relatorio(user_id=None)):
        with pytest.raises(HTTPException) as exc:
            execucao.gerar_playbook(GerarPlaybookRequest(relatorio_id="relatorio-1"), req)
    assert exc.value.status_code == 403


def test_execucao_gerar_owner_outro_usuario_nega():
    from backend.routers import execucao
    from backend.routers.execucao import GerarPlaybookRequest

    req = MagicMock()
    with patch.object(execucao, "_require_user", return_value="user-A"), \
         patch.object(execucao, "_sb", return_value=_sb_relatorio(user_id="user-B")):
        with pytest.raises(HTTPException) as exc:
            execucao.gerar_playbook(GerarPlaybookRequest(relatorio_id="relatorio-1"), req)
    assert exc.value.status_code == 403


def test_execucao_gerar_owner_vazio_string_nega():
    from backend.routers import execucao
    from backend.routers.execucao import GerarPlaybookRequest

    req = MagicMock()
    with patch.object(execucao, "_require_user", return_value="user-A"), \
         patch.object(execucao, "_sb", return_value=_sb_relatorio(user_id="")):
        with pytest.raises(HTTPException) as exc:
            execucao.gerar_playbook(GerarPlaybookRequest(relatorio_id="relatorio-1"), req)
    assert exc.value.status_code == 403
