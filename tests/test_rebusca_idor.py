"""Regressão IDOR em /rebuscar-candidatos (Opsera Finding #2).

Antes do fix, relatório com user_id vazio/ausente pulava o check de ownership
e qualquer JWT autenticado podia re-buscar candidatos.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


def _sb_relatorio(*, user_id, status="done"):
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.is_.return_value = chain
    chain.maybe_single.return_value = chain
    chain.execute.return_value = MagicMock(data={"id": "rel-1", "user_id": user_id, "status": status})
    sb = MagicMock()
    sb.table.return_value = chain
    return sb


@pytest.mark.asyncio
async def test_rebusca_owner_vazio_nega():
    from backend.routers import rebusca
    from backend.routers.rebusca import RebuscaRequest

    req = MagicMock()
    with patch.object(rebusca, "_require_user", return_value="user-A"), \
         patch.object(rebusca, "_sb", return_value=_sb_relatorio(user_id=None)):
        with pytest.raises(HTTPException) as exc:
            await rebusca.rebuscar_candidatos("rel-1", RebuscaRequest(), req)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_rebusca_owner_outro_usuario_nega():
    from backend.routers import rebusca
    from backend.routers.rebusca import RebuscaRequest

    req = MagicMock()
    with patch.object(rebusca, "_require_user", return_value="user-A"), \
         patch.object(rebusca, "_sb", return_value=_sb_relatorio(user_id="user-B")):
        with pytest.raises(HTTPException) as exc:
            await rebusca.rebuscar_candidatos("rel-1", RebuscaRequest(), req)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_rebusca_owner_vazio_string_nega():
    from backend.routers import rebusca
    from backend.routers.rebusca import RebuscaRequest

    req = MagicMock()
    with patch.object(rebusca, "_require_user", return_value="user-A"), \
         patch.object(rebusca, "_sb", return_value=_sb_relatorio(user_id="")):
        with pytest.raises(HTTPException) as exc:
            await rebusca.rebuscar_candidatos("rel-1", RebuscaRequest(), req)
    assert exc.value.status_code == 403
