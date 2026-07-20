"""Persistência de assistant quando o turno ADK explode."""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest


@contextmanager
def _fake_route(_agente):
    yield False


@pytest.mark.asyncio
async def test_run_site_agent_persiste_assistant_em_falha_llm():
    from agents_site.runner import run_site_agent_adk

    salvou: list[dict] = []

    async def _fake_salvar(projeto_id, role, content, **kwargs):
        salvou.append({"role": role, "content": content, **kwargs})
        return "msg-id"

    with (
        patch(
            "agents_site.runner.carregar_historico",
            new=AsyncMock(return_value=[]),
        ),
        patch("agents_site.runner.salvar_mensagem", side_effect=_fake_salvar),
        patch(
            "services.consultor.project_state.carregar_projeto",
            new=AsyncMock(side_effect=Exception("sem projeto em teste")),
        ),
        patch(
            "services.consultor.project_state.atualizar_campo_projeto",
            new=AsyncMock(),
        ),
        patch(
            "agents_site.runner._rodar_turno",
            new=AsyncMock(
                side_effect=Exception(
                    "403 PERMISSION_DENIED Lightning dunning decision is deny"
                )
            ),
        ),
        patch("agents_site.runner.site_chat_developer_api", _fake_route),
    ):
        out = await run_site_agent_adk(
            "pid-test",
            "quantas academias tem no Bessa?",
            agente="degustacao",
        )

    assert any(s["role"] == "user" for s in salvou)
    assistants = [s for s in salvou if s["role"] == "assistant"]
    assert len(assistants) == 1
    assert (
        "bloqueado" in assistants[0]["content"].lower()
        or "cobrança" in assistants[0]["content"].lower()
    )
    assert out == assistants[0]["content"]
