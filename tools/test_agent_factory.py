"""Testes determinísticos para tools/agent_factory.py::build_llm_agent.

Sem chamada LLM real. Usa mocks/monkeypatch para isolar ADK e telemetria.
"""
from __future__ import annotations

import sys
import os
import types as _types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import pytest


# ---------------------------------------------------------------------------
# Helpers de mock
# ---------------------------------------------------------------------------

class _FakeAgent:
    """Stub de google.adk.agents.Agent sem I/O."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _FakeGemini:
    """Stub de google.adk.models.google_llm.Gemini."""
    def __init__(self, model, retry_options=None):
        self.model = model
        self.retry_options = retry_options


class _FakeRetryOptions:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def _make_fake_adk(monkeypatch):
    """Injeta módulos ADK falsos no sys.modules para isolar build_llm_agent."""
    # google.adk.agents
    m_agents = _types.ModuleType("google.adk.agents")
    m_agents.Agent = _FakeAgent

    # google.adk.models.google_llm
    m_llm = _types.ModuleType("google.adk.models.google_llm")
    m_llm.Gemini = _FakeGemini

    # google.genai.types (para HttpRetryOptions)
    m_genai_types = _types.ModuleType("google.genai.types")
    m_genai_types.HttpRetryOptions = _FakeRetryOptions

    # google.genai
    m_genai = _types.ModuleType("google.genai")
    m_genai.types = m_genai_types

    # google.adk
    m_adk = _types.ModuleType("google.adk")
    m_adk.agents = m_agents

    # google.adk.models
    m_adk_models = _types.ModuleType("google.adk.models")

    # google
    m_google = _types.ModuleType("google")
    m_google.adk = m_adk
    m_google.genai = m_genai

    for name, mod in [
        ("google", m_google),
        ("google.adk", m_adk),
        ("google.adk.agents", m_agents),
        ("google.adk.models", m_adk_models),
        ("google.adk.models.google_llm", m_llm),
        ("google.genai", m_genai),
        ("google.genai.types", m_genai_types),
    ]:
        monkeypatch.setitem(sys.modules, name, mod)

    return m_agents, m_llm


def _import_fresh_factory(monkeypatch):
    """Reimporta agent_factory com ADK fake para garantir isolamento."""
    _make_fake_adk(monkeypatch)
    # Remove cache do módulo para forçar reimport com stubs
    monkeypatch.delitem(sys.modules, "tools.agent_factory", raising=False)
    monkeypatch.delitem(sys.modules, "agent_factory", raising=False)
    import importlib
    factory = importlib.import_module("tools.agent_factory")
    return factory


# ---------------------------------------------------------------------------
# 1. build_llm_agent retorna instância de Agent (stub)
# ---------------------------------------------------------------------------

def test_retorna_agente(monkeypatch):
    factory = _import_fresh_factory(monkeypatch)
    # Stub de telemetria para não tentar I/O de CSV
    def _noop_telemetry(ctx, resp):
        pass
    m_tel = _types.ModuleType("tools.token_telemetry")
    m_tel.after_model_callback = _noop_telemetry
    monkeypatch.setitem(sys.modules, "tools.token_telemetry", m_tel)

    agente = factory.build_llm_agent(
        name="teste",
        model="gemini-2.5-flash",
        instruction="Você é um agente de teste.",
    )
    assert isinstance(agente, _FakeAgent)


# ---------------------------------------------------------------------------
# 2. after_model_callback != None após build (telemetria injetada)
# ---------------------------------------------------------------------------

def test_after_model_callback_injetado(monkeypatch):
    factory = _import_fresh_factory(monkeypatch)

    def _noop_telemetry(ctx, resp):
        pass

    m_tel = _types.ModuleType("tools.token_telemetry")
    m_tel.after_model_callback = _noop_telemetry
    monkeypatch.setitem(sys.modules, "tools.token_telemetry", m_tel)

    agente = factory.build_llm_agent(
        name="teste",
        model="gemini-2.5-flash",
        instruction="Instrução.",
    )
    assert agente.after_model_callback is not None


# ---------------------------------------------------------------------------
# 3. Callback próprio + telemetria: resultado encadeia ambos
# ---------------------------------------------------------------------------

def test_callbacks_encadeados(monkeypatch):
    factory = _import_fresh_factory(monkeypatch)

    chamadas = {"proprio": 0, "telemetria": 0}

    def _meu_callback(ctx, resp):
        chamadas["proprio"] += 1

    def _telemetria(ctx, resp):
        chamadas["telemetria"] += 1

    m_tel = _types.ModuleType("tools.token_telemetry")
    m_tel.after_model_callback = _telemetria
    monkeypatch.setitem(sys.modules, "tools.token_telemetry", m_tel)

    agente = factory.build_llm_agent(
        name="teste",
        model="gemini-2.5-flash",
        instruction="Instrução.",
        after_model_callback=_meu_callback,
    )

    # O callback resultante deve ser o encadeado (_chained), não um dos originais
    cb = agente.after_model_callback
    assert cb is not _meu_callback
    assert cb is not _telemetria

    # Invocar o callback encadeado deve chamar AMBOS
    cb(None, None)
    assert chamadas["proprio"] == 1, "callback próprio não foi chamado"
    assert chamadas["telemetria"] == 1, "callback de telemetria não foi chamado"


def test_callbacks_encadeados_contagem_multipla(monkeypatch):
    """Invocar o callback encadeado N vezes incrementa ambos N vezes."""
    factory = _import_fresh_factory(monkeypatch)
    chamadas = {"proprio": 0, "telemetria": 0}

    def _meu(ctx, resp):
        chamadas["proprio"] += 1

    def _tel(ctx, resp):
        chamadas["telemetria"] += 1

    m_tel = _types.ModuleType("tools.token_telemetry")
    m_tel.after_model_callback = _tel
    monkeypatch.setitem(sys.modules, "tools.token_telemetry", m_tel)

    agente = factory.build_llm_agent(
        name="x",
        model="gemini-2.5-flash",
        instruction="i",
        after_model_callback=_meu,
    )
    cb = agente.after_model_callback
    for _ in range(3):
        cb(None, None)
    assert chamadas["proprio"] == 3
    assert chamadas["telemetria"] == 3


# ---------------------------------------------------------------------------
# 4. Se callback próprio já É a telemetria, NÃO duplica (não encadeia consigo)
# ---------------------------------------------------------------------------

def test_nao_encadeia_quando_proprio_e_telemetria(monkeypatch):
    factory = _import_fresh_factory(monkeypatch)
    chamadas = {"telemetria": 0}

    def _telemetria(ctx, resp):
        chamadas["telemetria"] += 1

    m_tel = _types.ModuleType("tools.token_telemetry")
    m_tel.after_model_callback = _telemetria
    monkeypatch.setitem(sys.modules, "tools.token_telemetry", m_tel)

    # Passa o próprio _telemetria como callback — não deve duplicar
    agente = factory.build_llm_agent(
        name="x",
        model="gemini-2.5-flash",
        instruction="i",
        after_model_callback=_telemetria,
    )
    cb = agente.after_model_callback
    cb(None, None)
    # deve ter chamado 1x (não 2x)
    assert chamadas["telemetria"] == 1


# ---------------------------------------------------------------------------
# 5. model string → objeto Gemini (ou mantém string se ADK ausente)
# ---------------------------------------------------------------------------

def test_model_string_vira_gemini(monkeypatch):
    factory = _import_fresh_factory(monkeypatch)

    def _noop(ctx, resp):
        pass

    m_tel = _types.ModuleType("tools.token_telemetry")
    m_tel.after_model_callback = _noop
    monkeypatch.setitem(sys.modules, "tools.token_telemetry", m_tel)

    agente = factory.build_llm_agent(
        name="x",
        model="gemini-2.5-flash",
        instruction="i",
    )
    # Pode ser _FakeGemini (ADK disponível) ou str (ADK ausente — tolerado)
    assert isinstance(agente.model, (_FakeGemini, str))


def test_model_gemini_tem_retry_options(monkeypatch):
    """Se ADK disponível, objeto Gemini deve ter retry_options configurado."""
    factory = _import_fresh_factory(monkeypatch)

    def _noop(ctx, resp):
        pass

    m_tel = _types.ModuleType("tools.token_telemetry")
    m_tel.after_model_callback = _noop
    monkeypatch.setitem(sys.modules, "tools.token_telemetry", m_tel)

    agente = factory.build_llm_agent(
        name="x",
        model="gemini-2.5-flash",
        instruction="i",
    )
    if isinstance(agente.model, _FakeGemini):
        assert agente.model.retry_options is not None
        assert agente.model.model == "gemini-2.5-flash"


# ---------------------------------------------------------------------------
# 6. Sem after_model_callback passado: callback injetado É a telemetria direta
# ---------------------------------------------------------------------------

def test_sem_callback_proprio_recebe_telemetria_direta(monkeypatch):
    factory = _import_fresh_factory(monkeypatch)
    chamadas = {"n": 0}

    def _tel(ctx, resp):
        chamadas["n"] += 1

    m_tel = _types.ModuleType("tools.token_telemetry")
    m_tel.after_model_callback = _tel
    monkeypatch.setitem(sys.modules, "tools.token_telemetry", m_tel)

    agente = factory.build_llm_agent(name="x", model="gemini-2.5-flash", instruction="i")
    # Callback deve ser a telemetria (ou um wrapper que a chama)
    agente.after_model_callback(None, None)
    assert chamadas["n"] == 1
