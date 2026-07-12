"""
Router /api/chat — agente conversacional "Diagnostico GymSite".

Persiste cada turno em `chat_interacoes` (Supabase) e responde com base numa
classificacao de intencao leve + base de conhecimento (KB). Quando a intencao
e "pesquisa_mercado", delega ao agente A7 (MarketResearch) do pipeline ADK.

Sessao: o front gera/reusa um session_id (uuid) e o envia em cada turno, para
costurar a conversa. user_id e opcional (landing anonima); quando o visitante
estiver logado no app, o JWT preenche user_id.

Tabela `chat_interacoes` (ja existe no schema):
  id, user_id, session_id, endpoint, pergunta, intencao, resposta, kb_fontes
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from supabase import create_client

logger = logging.getLogger("gymsite.chat")

router = APIRouter(prefix="/api/chat", tags=["Chat — Agente"])

_ENDPOINT_TAG = "landing-diagnostico"

# Intencoes reconhecidas pelo classificador leve. Mapeadas para handlers.
_INTENCOES = (
    "saudacao",
    "abrir_academia",
    "ja_opero",
    "pesquisa_mercado",
    "preco_produto",
    "pedir_diagnostico",
    "outro",
)


def _sb():
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise HTTPException(status_code=500, detail="Supabase nao configurado")
    return create_client(url, key)


def _maybe_user_id(request: Request) -> Optional[str]:
    """Best-effort: extrai user_id do JWT se presente; landing e anonima."""
    auth = request.headers.get("authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    if not token:
        return None
    try:
        user_resp = _sb().auth.get_user(token)
        user = user_resp.user if user_resp else None
        return user.id if user else None
    except Exception:
        return None


class ChatTurno(BaseModel):
    pergunta: str = Field(min_length=1, max_length=2000)
    session_id: str = Field(min_length=8, max_length=80)
    perfil: Optional[str] = Field(default=None, max_length=40)
    cidade: Optional[str] = Field(default=None, max_length=120)
    bairro: Optional[str] = Field(default=None, max_length=120)


class ChatResposta(BaseModel):
    resposta: str
    intencao: str
    session_id: str
    fontes: list[str] = []


def _classificar_intencao(texto: str) -> str:
    """Classificador heuristico barato (sem LLM) para o hot-path do chat.
    Mantido simples de proposito: o objetivo do agente da landing e qualificar
    e direcionar ao diagnostico, nao responder qualquer pergunta aberta."""
    t = (texto or "").lower()
    if any(w in t for w in ("oi", "ola", "bom dia", "boa tarde", "boa noite")):
        return "saudacao"
    if any(w in t for w in ("quero abrir", "vou abrir", "pretendo abrir", "abrir uma")):
        return "abrir_academia"
    if any(w in t for w in ("ja opero", "ja tenho", "minha academia", "ja sou dono")):
        return "ja_opero"
    if any(w in t for w in ("preco", "quanto custa", "valor", "plano", "assinatura")):
        return "preco_produto"
    if any(w in t for w in ("relatorio", "diagnostico", "analise", "viabilidade")):
        return "pedir_diagnostico"
    if any(w in t for w in ("mercado", "tendencia", "concorrencia", "demanda")):
        return "pesquisa_mercado"
    return "outro"


def _responder(intencao: str, turno: ChatTurno) -> tuple[str, list[str]]:
    """Resposta determinística por intencao (KB curta). 'pesquisa_mercado'
    pode delegar ao A7; aqui mantemos um fallback seguro caso o ADK nao
    esteja disponivel no processo da landing."""
    fontes: list[str] = []
    if intencao == "saudacao":
        return (
            "Ola! Sou o Diagnostico GymSite. Posso avaliar a viabilidade de um "
            "ponto para academia em minutos. Voce ja opera uma academia ou "
            "pretende abrir uma?",
            fontes,
        )
    if intencao in ("abrir_academia", "ja_opero", "pedir_diagnostico"):
        return (
            "Perfeito. Me diga a cidade e o bairro de interesse que eu preparo "
            "um diagnostico de viabilidade (concorrencia, demografia e cenario "
            "financeiro). Voce tambem pode deixar seu contato para receber o "
            "relatorio completo.",
            fontes,
        )
    if intencao == "preco_produto":
        return (
            "O diagnostico GymSite gera um relatorio executivo por ponto "
            "analisado. Posso te conectar com o time comercial para os planos "
            "atuais — me deixa seu nome e e-mail?",
            fontes,
        )
    if intencao == "pesquisa_mercado":
        resposta, fontes = _pesquisa_mercado_a7(turno)
        return resposta, fontes
    return (
        "Posso ajudar com a viabilidade de pontos para academia. Quer que eu "
        "comece um diagnostico para uma cidade e bairro especificos?",
        fontes,
    )


def _pesquisa_mercado_a7(turno: ChatTurno) -> tuple[str, list[str]]:
    """Delega ao agente A7 (MarketResearch) se o ADK estiver disponivel.
    Fallback seguro: orienta o visitante a pedir o diagnostico completo."""
    try:
        from tools.market_research_bridge import responder_pergunta_mercado

        out = responder_pergunta_mercado(
            pergunta=turno.pergunta,
            cidade=turno.cidade,
            bairro=turno.bairro,
        )
        return out.get("resposta", ""), out.get("fontes", [])
    except Exception as e:  # noqa: BLE001
        logger.info("A7 indisponivel no processo da landing (%s); fallback", e)
        return (
            "Para uma leitura de mercado confiavel desse bairro, o ideal e rodar "
            "o diagnostico completo — ele cruza IBGE, concorrentes e cenario "
            "financeiro. Quer que eu inicie?",
            [],
        )


def _persistir_interacao(
    sb,
    *,
    user_id: Optional[str],
    session_id: str,
    pergunta: str,
    intencao: str,
    resposta: str,
    fontes: list[str],
) -> None:
    try:
        sb.table("chat_interacoes").insert({
            "user_id": user_id,
            "session_id": session_id,
            "endpoint": _ENDPOINT_TAG,
            "pergunta": pergunta[:2000],
            "intencao": intencao,
            "resposta": resposta[:4000],
            "kb_fontes": fontes or None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:  # noqa: BLE001
        # Persistencia e telemetria — nunca quebra a conversa do visitante.
        logger.warning("chat_interacoes insert falhou (segue): %s", e)


@router.post("", response_model=ChatResposta)
async def conversar(turno: ChatTurno, request: Request):
    """Um turno da conversa do agente da landing."""
    sb = _sb()
    user_id = _maybe_user_id(request)

    intencao = _classificar_intencao(turno.pergunta)
    resposta, fontes = _responder(intencao, turno)

    _persistir_interacao(
        sb,
        user_id=user_id,
        session_id=turno.session_id,
        pergunta=turno.pergunta,
        intencao=intencao,
        resposta=resposta,
        fontes=fontes,
    )

    logger.info(
        "chat turno session=%s intencao=%s user=%s",
        turno.session_id, intencao, user_id or "anon",
    )
    return ChatResposta(
        resposta=resposta,
        intencao=intencao,
        session_id=turno.session_id,
        fontes=fontes,
    )
