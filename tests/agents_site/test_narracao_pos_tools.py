"""Narração Ollama pós-tools: persona por tool + Consultor reforça texto vazio."""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest


def test_persona_engenheiro_quando_tool_hvac():
    from agents_site.runner import _persona_narracao_pos_tools

    prompt = _persona_narracao_pos_tools(
        [{"ferramenta": "consultar_engenharia_obra", "resultado": {"ok": True}}],
    )
    assert "Engenheiro de Obra" in prompt
    assert "NBR 16401" in prompt


def test_persona_generica_quando_tool_mercado():
    from agents_site.runner import _persona_narracao_pos_tools

    prompt = _persona_narracao_pos_tools(
        [{"ferramenta": "analisar_demografia", "resultado": {"renda": 1}}],
        autor="Mercado",
    )
    assert "Engenheiro de Obra" not in prompt
    assert "NBR 16401" not in prompt
    assert "GymSite" in prompt


def test_persona_engenheiro_pelo_autor_sem_tool_hvac():
    from agents_site.runner import _persona_narracao_pos_tools

    prompt = _persona_narracao_pos_tools(
        [{"ferramenta": "consultar_catalogo_equipamentos", "resultado": {}}],
        autor="EngenheiroObra",
    )
    assert "Engenheiro de Obra" in prompt


@contextmanager
def _fake_route(_agente):
    yield False


@pytest.mark.asyncio
async def test_consultor_narra_quando_resposta_vazia_com_tools_ollama():
    from agents_site.runner import run_consultor_adk

    salvou: list[dict] = []

    async def _fake_salvar(projeto_id, role, content, **kwargs):
        salvou.append({"role": role, "content": content, **kwargs})
        return "msg-id"

    acoes = [
        {
            "ferramenta": "analisar_demografia",
            "status": "sucesso",
            "resumo": "analisar_demografia",
            "resultado": {"pop": 1000},
        }
    ]

    with (
        patch(
            "agents_site.runner.carregar_historico",
            new=AsyncMock(return_value=[]),
        ),
        patch("agents_site.runner.salvar_mensagem", side_effect=_fake_salvar),
        patch(
            "agents_site.runner._rodar_turno",
            new=AsyncMock(return_value=("", "Mercado", None, acoes)),
        ),
        patch(
            "agents_site.runner._retry_pos_transfer",
            new=AsyncMock(return_value=("", None, None)),
        ),
        patch("agents_site.runner.site_chat_developer_api", _fake_route),
        patch(
            "agents_site.runner._sync_consultor_pos_turno",
            new=AsyncMock(),
        ),
        patch("agents_site.runner.using_ollama", return_value=True),
        patch(
            "agents_site.runner._narrar_pos_tools_ollama",
            return_value="População estimada: 1000 hab no raio consultado.",
        ) as narrar,
    ):
        out = await run_consultor_adk(
            "pid-c",
            "qual a demografia?",
            usuario_id="u1",
            agente="mercado",
        )

    narrar.assert_called()
    assert "1000" in out
    assistants = [s for s in salvou if s["role"] == "assistant"]
    assert len(assistants) == 1
    assert "1000" in assistants[0]["content"]


def test_narrar_usa_persona_generica_para_demografia(monkeypatch):
    from agents_site import runner as runner_mod

    monkeypatch.setattr(runner_mod, "using_ollama", lambda: True)

    captured: dict = {}

    class _Choice:
        def __init__(self, content: str):
            self.message = type("M", (), {"content": content})()

    class _Resp:
        choices = [_Choice("Renda média ok.")]

    def _fake_completion(**kwargs):
        captured["messages"] = kwargs["messages"]
        return _Resp()

    fake_litellm = type("L", (), {"completion": staticmethod(_fake_completion)})()

    with patch.dict("sys.modules", {"litellm": fake_litellm}):
        text = runner_mod._narrar_pos_tools_ollama(
            "renda do bairro?",
            [{"ferramenta": "analisar_demografia", "resultado": {"renda": 4200}}],
            autor="Mercado",
        )

    assert text == "Renda média ok."
    user_prompt = captured["messages"][0]["content"]
    assert "Engenheiro de Obra" not in user_prompt
    assert "analisar_demografia" in user_prompt
