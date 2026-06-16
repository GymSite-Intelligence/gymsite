"""A5 ContactHunter convertido p/ determinístico (sem LLM)."""
from agents.a5_contact_hunter import ContactHunterAgent, _StateShim, contact_hunter_agent
from tools.contact_tools import gerar_contato_decisor_completo


def test_agente_e_baseagent():
    from google.adk.agents import BaseAgent

    assert isinstance(contact_hunter_agent, BaseAgent)
    assert isinstance(contact_hunter_agent, ContactHunterAgent)
    assert contact_hunter_agent.name == "ContactHunter"


def test_macro_state_vazio_nao_crasha():
    # A macro degrada com defaults — nunca derruba o pipeline.
    r = gerar_contato_decisor_completo(_StateShim({}))
    assert isinstance(r, dict)
    assert r.get("script_abordagem")  # campo de maior valor sempre presente
    assert r.get("canal_recomendado")


def test_state_shim_so_expoe_state():
    sh = _StateShim({"a": 1})
    assert sh.state == {"a": 1}
    assert set(_StateShim.__slots__) == {"state"}
