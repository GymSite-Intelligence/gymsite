"""
Guardrails do modo DEGUSTAÇÃO (público, landing) — port do gate do consultor_engine
para o ADK, via before_tool_callback.

Tier vem de session.state["tier"]:
  - "degustacao" (landing pública): gate HARD ON — bloqueia tools de Tier 2 e corta
    amostras após K=2 (antifatiamento).
  - qualquer outro / ausente (consultor logado): SEM gate (acesso completo).

before_tool_callback(tool, args, tool_context) → se retorna dict, esse dict vira o
RESULTADO da tool (a tool real NÃO roda). É a barreira real, independe do prompt.
"""
from __future__ import annotations

# Tools que só existem no diagnóstico completo (Tier 2) — bloqueadas na degustação.
_BLOQUEADAS_DEGUSTACAO = frozenset({
    "estimar_investimento",
    "buscar_pontos_comerciais",
    "gerar_relatorio_formal",
})

# Tools de "amostra detalhada" (dado real e caro) — contam pro antifatiamento.
_AMOSTRA_TOOLS = frozenset({
    "analisar_demografia",
    "buscar_concorrentes",
    "pesquisar_contexto_mercado",
    "analisar_reviews_e_dores",
})

_MAX_AMOSTRAS = 2

_GATE_MSG = (
    "Essa análise mais detalhada faz parte do diagnóstico completo. Posso liberar agora — "
    "me passa nome + e-mail (ou WhatsApp) e os dados do projeto (estado, município, bairro, "
    "tipo de negócio, porte, público e gênero-alvo) que eu gero o relatório gratuito pra você."
)


def _bloqueio(ferramenta: str, motivo: str) -> dict:
    return {"bloqueado": True, "mensagem": _GATE_MSG,
            "_meta": {"ferramenta": ferramenta, "tier": motivo}}


def gate_degustacao(tool, args, tool_context):
    """before_tool_callback ADK: aplica o gate da degustação (tier público).
    Retorna None = deixa a tool rodar; retorna dict = bloqueia com a mensagem de gate."""
    state = getattr(tool_context, "state", None)
    if state is None:
        return None
    if state.get("tier") != "degustacao":
        return None  # consultor logado / teste: sem gate

    nome = getattr(tool, "name", None) or getattr(tool, "__name__", "")

    if nome in _BLOQUEADAS_DEGUSTACAO:
        return _bloqueio(nome, "bloqueada")

    if nome in _AMOSTRA_TOOLS:
        usadas = int(state.get("amostras", 0) or 0)
        if usadas >= _MAX_AMOSTRAS:
            return _bloqueio(nome, "limite_amostras")
        state["amostras"] = usadas + 1

    return None
