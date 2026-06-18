"""Testes determinísticos — A1 GeoScout (sem LLM / sem rede).

Foco: _persistir_macro_no_state (RN-A1-07) e contrato estático do agente.
Sem nenhuma chamada real a Google Maps ou LLM.
"""
from __future__ import annotations

import types

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_tool(name: str):
    """Objeto mínimo que imita FunctionTool com .name."""
    t = types.SimpleNamespace()
    t.name = name
    return t


def _fake_tool_context(state: dict | None = None):
    """Contexto mínimo com .state dict."""
    ctx = types.SimpleNamespace()
    ctx.state = state if state is not None else {}
    return ctx


# ---------------------------------------------------------------------------
# Importação do módulo — deve ser possível sem credenciais Google
# ---------------------------------------------------------------------------

def test_modulo_importavel():
    """O módulo agents.a1_geoscout deve importar sem travar ou exigir credenciais."""
    import agents.a1_geoscout  # noqa: F401


def test_funcao_persistir_exportada():
    """_persistir_macro_no_state deve estar acessível no módulo."""
    import agents.a1_geoscout as m

    assert callable(m._persistir_macro_no_state)


# ---------------------------------------------------------------------------
# Testes de _persistir_macro_no_state
# ---------------------------------------------------------------------------

class TestPersistirMacroNoState:
    """RN-A1-07: grava output da macro em candidatos_geoscout_pronto."""

    @pytest.fixture(autouse=True)
    def _load(self):
        import agents.a1_geoscout as m
        self.fn = m._persistir_macro_no_state

    # Caso feliz: tool correta + response dict → deve gravar
    def test_grava_quando_tool_certa_e_response_dict(self):
        state = {}
        ctx = _fake_tool_context(state)
        tool = _fake_tool("analisar_pontos_comerciais_completo")
        response = {"candidatos": [{"nome": "Anchor A"}], "total_candidatos": 1}

        result = self.fn(tool, {}, ctx, response)

        assert result is None  # callback ADK deve retornar None
        assert ctx.state["candidatos_geoscout_pronto"] is response

    # Nome de tool diferente → NÃO deve gravar
    def test_nao_grava_quando_tool_diferente(self):
        state = {}
        ctx = _fake_tool_context(state)
        tool = _fake_tool("outra_tool_qualquer")
        response = {"candidatos": []}

        self.fn(tool, {}, ctx, response)

        assert "candidatos_geoscout_pronto" not in ctx.state

    # Tool correta mas response não é dict (ex: string, lista) → NÃO grava
    def test_nao_grava_quando_response_nao_eh_dict(self):
        state = {}
        ctx = _fake_tool_context(state)
        tool = _fake_tool("analisar_pontos_comerciais_completo")

        for response in ["string", None, ["lista"], 42]:
            ctx.state.clear()
            self.fn(tool, {}, ctx, response)
            assert "candidatos_geoscout_pronto" not in ctx.state, (
                f"Não deveria gravar para response={response!r}"
            )

    # Tool sem atributo .name → tolera e não explode
    def test_tolera_tool_sem_attr_name(self):
        state = {}
        ctx = _fake_tool_context(state)
        tool_sem_name = object()  # sem .name

        # Não deve levantar exceção
        result = self.fn(tool_sem_name, {}, ctx, {"candidatos": []})

        assert result is None
        assert "candidatos_geoscout_pronto" not in ctx.state

    # State pré-existente não é apagado por chamada de tool diferente
    def test_state_preexistente_preservado_em_tool_diferente(self):
        state = {"chave_existente": "valor"}
        ctx = _fake_tool_context(state)
        tool = _fake_tool("outra_tool")
        response = {"candidatos": []}

        self.fn(tool, {}, ctx, response)

        assert ctx.state["chave_existente"] == "valor"

    # Segunda chamada com tool correta sobrescreve a chave (comportamento esperado)
    def test_sobrescreve_chave_em_segunda_chamada(self):
        state = {"candidatos_geoscout_pronto": {"candidatos": [], "total_candidatos": 0}}
        ctx = _fake_tool_context(state)
        tool = _fake_tool("analisar_pontos_comerciais_completo")
        novo_response = {"candidatos": [{"nome": "B"}], "total_candidatos": 1}

        self.fn(tool, {}, ctx, novo_response)

        assert ctx.state["candidatos_geoscout_pronto"] is novo_response

    # Dict vazio ainda é dict → grava (é um resultado válido de erro retornado pela macro)
    def test_grava_dict_vazio(self):
        state = {}
        ctx = _fake_tool_context(state)
        tool = _fake_tool("analisar_pontos_comerciais_completo")

        self.fn(tool, {}, ctx, {})

        assert "candidatos_geoscout_pronto" in ctx.state
        assert ctx.state["candidatos_geoscout_pronto"] == {}


# ---------------------------------------------------------------------------
# Testes de contrato estático do agente
# ---------------------------------------------------------------------------

class TestContratoEstaticoGeoscout:
    """Valida configuração do agente sem instanciar LLM real."""

    @pytest.fixture(autouse=True)
    def _load(self):
        import agents.a1_geoscout as m
        self.agent = m.geoscout_agent
        self.fn = m._persistir_macro_no_state

    def test_output_key_correto(self):
        """RN-A1 spec: output_key deve ser 'candidatos_geoscout'."""
        assert self.agent.output_key == "candidatos_geoscout"

    def test_nome_agente_correto(self):
        assert self.agent.name == "GeoScout"

    def test_after_tool_callback_eh_persistir_macro(self):
        """RN-A1-07: after_tool_callback deve ser _persistir_macro_no_state."""
        assert self.agent.after_tool_callback is self.fn

    def test_description_nao_vazia(self):
        assert self.agent.description and len(self.agent.description.strip()) > 0

    def test_instruction_nao_vazia(self):
        assert self.agent.instruction and len(str(self.agent.instruction).strip()) > 0

    def test_tem_exatamente_uma_tool(self):
        """RN-A1-01: único ponto de entrada é a macro-tool."""
        assert self.agent.tools is not None
        assert len(self.agent.tools) == 1

    def test_tool_e_analisar_pontos_comerciais_completo(self):
        """RN-A1-01: a tool deve ser analisar_pontos_comerciais_completo."""
        tool = self.agent.tools[0]
        # Pode ser callable direto ou objeto com .name
        name = getattr(tool, "name", None) or getattr(tool, "__name__", None) or ""
        assert "analisar_pontos_comerciais_completo" in name
