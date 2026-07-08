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

AGENTES_VALIDOS: frozenset[str] = frozenset({DEGUSTACAO, *ESPECIALISTAS})
