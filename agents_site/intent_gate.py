"""Gates determinísticos do chat de degustação: intenção sanitária e grounding.

O LLM não escolhe a fonte. Código pina o especialista, bloqueia tool errada
e recusa checklist municipal inventado quando a RAG não cobriu.
"""
from __future__ import annotations

from typing import Any

from tools.bairro_normalize import fold_texto

MSG_ABSTENCAO_SANITARIA = (
    "Não tenho na base a lista oficial da Vigilância Sanitária desse município. "
    "Os documentos que precisam ficar no local mudam conforme o CNAE e o que a "
    "lanchonete serve. Confirma o protocolo no setor de Vigilância da prefeitura "
    "— não monto checklist de memória."
)

_BLOQUEIO_SANITARIO_MAPS = (
    "Essa pergunta é de documentação sanitária, não de concorrência no mapa. "
    "Não busco academias para responder alvará da Vigilância."
)

_BLOQUEIO_LUGAR_INVALIDO = (
    "Não consegui um bairro e uma cidade válidos para buscar no mapa. "
    "Diz o bairro, a cidade e o estado (ex.: Centro, Navegantes, SC)."
)

_SANITARIA_HINTS = (
    "vigilancia sanitaria",
    "vigilancia sanit",
    "alvara sanitario",
    "licenca sanitaria",
    "documentacoes necessarias",
    "documentacao necessaria",
    "rdc 216",
    "boas praticas",
    "manipulador",
)

_SANITARIA_TOKENS = (
    "vigilancia",
    "sanitaria",
    "sanitario",
    "alvara",
    "pop",
    "pops",
)

_TOOLS_RAG_REGULATORIO = frozenset({
    "consultar_base_regulatoria",
    "consultar_eros_regulatorio",
})

_TOOLS_MAPS = frozenset({
    "buscar_concorrentes",
    "analisar_reviews_e_dores",
    "analisar_demografia",
    "pesquisar_contexto_mercado",
})

_VERBO_LUGAR = frozenset({
    "poderia", "indicar", "quais", "eles", "itens", "lista",
    "registro", "documentacao", "documentacoes", "necessarias",
    "vigilancia", "sanitaria", "sanitario", "apreciacao",
    "manter", "atualizado", "informada", "lanchonete", "devo",
    "solicitadas", "necessaria", "local",
})


def intencao_sanitaria(mensagem: str) -> bool:
    folded = fold_texto(mensagem or "")
    if not folded:
        return False
    if any(h in folded for h in _SANITARIA_HINTS):
        return True
    hits = sum(1 for t in _SANITARIA_TOKENS if t in folded.split() or t in folded)
    if "vigilancia" in folded and ("sanit" in folded or "document" in folded or "lanchonete" in folded):
        return True
    return hits >= 2 and ("document" in folded or "licenc" in folded or "alvara" in folded)


def parece_lugar(texto: str) -> bool:
    raw = (texto or "").strip()
    if not raw or raw in {"-", "–", "—", ".", ","}:
        return False
    folded = fold_texto(raw)
    if folded.startswith("cidade e ") or folded.startswith("cidade eh "):
        return False
    palavras = [p for p in folded.replace("-", " ").split() if p]
    if len(palavras) > 5:
        return False
    if any(p in _VERBO_LUGAR for p in palavras):
        return False
    return True


def loc_args_confiaveis(args: dict[str, Any] | None) -> bool:
    if not isinstance(args, dict):
        return False
    cidade = str(args.get("cidade") or "").strip()
    bairro = str(args.get("bairro") or "").strip()
    if not cidade or not bairro:
        return False
    return parece_lugar(cidade) and parece_lugar(bairro)


def loc_resolvida_confiavel(loc: Any) -> bool:
    bairro = getattr(loc, "bairro", "") or ""
    cidade = getattr(loc, "cidade", "") or ""
    if not (bairro or cidade):
        return False
    if cidade and not parece_lugar(cidade):
        return False
    if bairro and not parece_lugar(bairro):
        return False
    return True


def pin_especialista(agente: str, mensagem: str) -> str:
    """Quando o roteador (degustacao) ou Mercado receber sanitário → Regulatório."""
    if not intencao_sanitaria(mensagem):
        return agente
    if agente in ("degustacao", "mercado", ""):
        return "regulatorio"
    return agente


def _rag_regulatorio_ok(acoes: list[dict] | None) -> bool:
    for a in acoes or []:
        nome = (a.get("ferramenta") or a.get("resumo") or "").strip()
        if nome not in _TOOLS_RAG_REGULATORIO:
            continue
        res = a.get("resultado") if isinstance(a.get("resultado"), dict) else {}
        n = int(res.get("n_docs") or 0)
        texto = (res.get("texto_rag") or "").strip()
        if n > 0 or texto:
            return True
    return False


def aplicar_gate_grounding_sanitaria(
    mensagem: str,
    resposta: str,
    autor: str | None,
    acoes: list[dict] | None,
) -> tuple[str, str | None, list[dict]]:
    if not intencao_sanitaria(mensagem):
        return resposta, autor, acoes or []
    if _rag_regulatorio_ok(acoes):
        return resposta, autor or "Regulatorio", acoes or []
    return MSG_ABSTENCAO_SANITARIA, "Regulatorio", []


def mensagem_bloqueio_maps(args: dict | None, user_message: str) -> str | None:
    if intencao_sanitaria(user_message):
        return _BLOQUEIO_SANITARIO_MAPS
    if args and not loc_args_confiaveis(args):
        return _BLOQUEIO_LUGAR_INVALIDO
    return None


def ferramenta_maps(nome: str) -> bool:
    return nome in _TOOLS_MAPS
