"""Catálogo dos agentes da degustação: id público (API) → nome do Agent ADK.

FONTE ÚNICA. O backend valida o `agente` recebido contra estas chaves e o runner
resolve por aqui qual especialista responde. Sem isso o id vira string livre: entra
cru na chave do Redis do cap (`site_chat:agente:{ip}:{agente}:{dia}`) e a escolha do
usuário não fixa quem responde — o roteador decide sozinho.

Módulo deliberadamente sem dependências (não importa `google.adk`): o backend precisa
validar sem pagar o import do ADK na subida da api.
"""

from __future__ import annotations

# id público (o que o front manda) → name do Agent em agents_site/agent.py
ESPECIALISTAS: dict[str, str] = {
    "responsavel_tecnico": "ResponsavelTecnico",
    "arquiteto": "Arquiteto",
    "engenheiro_obra": "EngenheiroObra",
    "regulatorio": "Regulatorio",
    "mercado": "Mercado",
}

# Sem especialista escolhido: o roteador (GymSiteSite) decide pra quem transferir.
DEGUSTACAO = "degustacao"
ROTEADOR_ADK = "GymSiteSite"

AGENTES_VALIDOS: frozenset[str] = frozenset({DEGUSTACAO, *ESPECIALISTAS})

# Inverso: `project_messages.agente` guarda o nome ADK (Event.author), mas a API fala id
# público nos DOIS sentidos — senão o front precisaria de um segundo mapa (P-008).
_ADK_PARA_ID: dict[str, str] = {nome: _id for _id, nome in ESPECIALISTAS.items()}
_ADK_PARA_ID[ROTEADOR_ADK] = DEGUSTACAO


def id_publico(nome_adk: str | None) -> str | None:
    """Nome do Agent ADK → id público. Desconhecido/None → None (front não acende crachá)."""
    return _ADK_PARA_ID.get(nome_adk) if nome_adk else None
