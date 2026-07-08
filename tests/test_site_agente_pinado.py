"""Degustação: o especialista escolhido responde de fato, e o `agente` é validado.

Antes disto o `agente` era string livre (entrava cru na chave do Redis do cap) e o runner
sempre rodava o roteador — clicar em "Regulatório" podia devolver o Mercado.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agents_site.catalog import AGENTES_VALIDOS, DEGUSTACAO, ESPECIALISTAS


# ─── A. validação do `agente` (P-005) ────────────────────────────────────────

def test_agente_invalido_e_recusado():
    from backend.routers.site_agent import ConversarSiteInput

    with pytest.raises(ValidationError):
        ConversarSiteInput(mensagem="oi", agente="regulatorio; DROP")


def test_agente_forjado_nao_fura_o_cap():
    """O cap é keyed por `agente`. String livre = contador novo a cada request."""
    from backend.routers.site_agent import ConversarSiteInput

    for forjado in ("x1", "x2", "regulatorio:extra", ""):
        with pytest.raises(ValidationError):
            ConversarSiteInput(mensagem="oi", agente=forjado)


def test_agentes_do_catalogo_sao_aceitos():
    from backend.routers.site_agent import ConversarSiteInput

    for valido in AGENTES_VALIDOS:
        assert ConversarSiteInput(mensagem="oi", agente=valido).agente == valido


def test_agente_ausente_continua_valido():
    from backend.routers.site_agent import ConversarSiteInput

    assert ConversarSiteInput(mensagem="oi").agente is None


# ─── B. o especialista escolhido roda como raiz ──────────────────────────────

def test_catalogo_bate_com_os_sub_agentes_do_roteador():
    """Se alguém renomear um Agent, o catálogo quebra aqui — não em produção."""
    from agents_site.agent import root_agent

    nomes = {a.name for a in root_agent.sub_agents}
    assert set(ESPECIALISTAS.values()) == nomes


def test_degustacao_resolve_para_o_roteador():
    from agents_site.agent import root_agent
    from agents_site.runner import _resolver_agente

    assert _resolver_agente(DEGUSTACAO) is root_agent
    assert _resolver_agente("desconhecido") is root_agent


@pytest.mark.parametrize("agente_id,nome_adk", sorted(ESPECIALISTAS.items()))
def test_especialista_pinado_responde_ele_mesmo(agente_id, nome_adk):
    from agents_site.runner import _resolver_agente

    assert _resolver_agente(agente_id).name == nome_adk


@pytest.mark.parametrize("agente_id", sorted(ESPECIALISTAS))
def test_especialista_pinado_nao_pode_transferir(agente_id):
    """O nó da regressão.

    O ADK só usa SingleFlow (sem a tool transfer_to_agent) quando as DUAS flags de
    disallow estão ligadas E não há sub_agents. O especialista original tem
    `parent_agent` = roteador ⇒ AutoFlow ⇒ ganharia pai e irmãos como alvos, e o
    Regulatório fixado saltaria pro Mercado.
    """
    from google.adk.flows.llm_flows.single_flow import SingleFlow
    from agents_site.runner import _resolver_agente

    pinado = _resolver_agente(agente_id)
    assert pinado.parent_agent is None
    assert pinado.disallow_transfer_to_parent is True
    assert pinado.disallow_transfer_to_peers is True
    assert not pinado.sub_agents
    assert isinstance(pinado._llm_flow, SingleFlow)


def test_pinar_nao_muda_o_roteador():
    """As cópias não podem contaminar os sub_agents do roteador."""
    from agents_site.agent import root_agent
    from agents_site.runner import _resolver_agente

    _resolver_agente("regulatorio")  # força a construção das cópias
    for sub in root_agent.sub_agents:
        assert sub.parent_agent is root_agent
