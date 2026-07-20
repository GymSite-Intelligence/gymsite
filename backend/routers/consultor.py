"""
CONSULTOR V2 — Endpoints FastAPI
=================================
Cole estas rotas no api.py existente, abaixo dos endpoints /api/assistente/*.

Prefixo: /api/consultor/
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from pydantic import BaseModel, Field
from typing import Optional, List

from agents_site.catalog import AGENTES_VALIDOS, id_publico
from services.consultor.consultor_engine import disparar_relatorio_formal
from services.consultor.project_state import (
    listar_projetos,
    carregar_projeto,
    criar_projeto,
    arquivar_projeto,
    atualizar_status,
    _row_to_state,
    _client,
)
from services.consultor.project_messages import carregar_historico_completo

router_consultor = APIRouter(prefix="/api/consultor", tags=["consultor-v2"])


def _auth_user_id(request: Request) -> str:
    """Resolve o user_id autenticado via o mecanismo real do api.py
    (_resolve_user_and_org). Import LAZY p/ evitar circular (api.py importa este
    módulo ao montar o router). 401 quando não autenticado — o consultor exige
    user real (RLS em user_projects.user_id)."""
    from api import _resolve_user_and_org

    user_id, _org = _resolve_user_and_org(request)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Autenticação necessária para o Consultor.")
    return user_id


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ConversarInput(BaseModel):
    mensagem: str = Field(..., min_length=1, max_length=4000)
    projeto_id: Optional[str] = None
    agente: Optional[str] = None


class ConversarEnqueueOutput(BaseModel):
    projeto_id: str
    status: str = "analisando"



class RelatorioInput(BaseModel):
    incluir_secoes: list[str] = Field(default_factory=list)


# ─── POST /api/consultor/conversar ────────────────────────────────────────────

@router_consultor.post("/conversar", response_model=ConversarEnqueueOutput)
async def consultor_conversar(
    body: ConversarInput,
    request: Request,
    background: BackgroundTasks,
):
    """Enfileira turno ADK. Resposta vem por GET /projetos/{id}/mensagens."""
    from api import _enqueue_ou_background

    user_id = _auth_user_id(request)
    agente = body.agente or "degustacao"
    if agente not in AGENTES_VALIDOS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agente inválido.")

    try:
        if body.projeto_id:
            await carregar_projeto(body.projeto_id, user_id)
            projeto_id = body.projeto_id
        else:
            projeto = await criar_projeto(user_id)
            projeto_id = projeto.id
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    await _enqueue_ou_background(
        {
            "type": "consultor_conversar",
            "projeto_id": projeto_id,
            "mensagem": body.mensagem,
            "usuario_id": user_id,
            "agente": agente,
        },
        background,
    )
    return ConversarEnqueueOutput(projeto_id=projeto_id, status="analisando")


# ─── GET /api/consultor/projetos/{projeto_id}/mensagens ───────────────────────

@router_consultor.get("/projetos/{projeto_id}/mensagens")
async def consultor_mensagens(
    projeto_id: str,
    request: Request,
    desde: Optional[str] = None,
):
    """Polling do chat logado — mensagens após `desde` (ISO) + estado do projeto."""
    user_id = _auth_user_id(request)
    try:
        projeto = await carregar_projeto(projeto_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    db = _client()
    from tools.db_schema import tbl

    q = (
        tbl(db, "project_messages")
        .select("role, content, created_at, agente, tool_calls, tool_results")
        .eq("projeto_id", projeto_id)
    )
    if desde:
        q = q.gt("created_at", desde)
    msgs = q.order("created_at").execute().data or []
    from agents_site.carimbo import unpack_citacoes_from_msg

    for m in msgs:
        m["agente"] = id_publico(m.get("agente"))
        m["citacoes"] = unpack_citacoes_from_msg(m)
        m.pop("tool_results", None)

    pesq = projeto.pesquisas_realizadas or {}
    pode_relatorio = bool(
        (projeto.localizacao or {}).get("cidade")
        and (projeto.localizacao or {}).get("bairro")
        and (pesq.get("concorrentes") or pesq.get("investimento"))
    )

    return {
        "mensagens": msgs,
        "status": projeto.status,
        "pode_gerar_relatorio": pode_relatorio,
        "localizacao": projeto.localizacao or {},
        "modelo_negocio": projeto.modelo_negocio or {},
        "pesquisas_realizadas": pesq,
        "custo_brl_ate_agora": projeto.custo_brl_ate_agora,
        "relatorio_id": projeto.relatorio_id,
    }


# ─── GET /api/consultor/projetos ──────────────────────────────────────────────

@router_consultor.get("/projetos")
async def listar_projetos_usuario(request: Request):
    """Lista projetos ativos do usuário (max 20, ordenados por updated_at desc)."""
    user_id = _auth_user_id(request)
    projetos = await listar_projetos(user_id)
    return {
        "projetos": [
            {
                "id": p.id,
                "status": p.status,
                "cidade": (p.localizacao or {}).get("cidade"),
                "bairro": (p.localizacao or {}).get("bairro"),
                "uf": (p.localizacao or {}).get("uf"),
                "pesquisas_realizadas": p.pesquisas_realizadas,
                "custo_brl_ate_agora": p.custo_brl_ate_agora,
                "relatorio_id": p.relatorio_id,
                "updated_at": p.updated_at,
                "created_at": p.created_at,
            }
            for p in projetos
        ]
    }


# ─── GET /api/consultor/projetos/{projeto_id} ─────────────────────────────────

@router_consultor.get("/projetos/{projeto_id}")
async def detalhe_projeto(
    projeto_id: str,
    request: Request,
):
    """
    Retorna projeto + histórico de mensagens.
    Usado pelo frontend para: polling de status, carregar sessão existente.
    """
    user_id = _auth_user_id(request)
    try:
        projeto = await carregar_projeto(projeto_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    mensagens = await carregar_historico_completo(projeto_id)
    from agents_site.carimbo import unpack_citacoes_from_msg

    return {
        "projeto": {
            "id": projeto.id,
            "status": projeto.status,
            "localizacao": projeto.localizacao,
            "modelo_negocio": projeto.modelo_negocio,
            "pesquisas_realizadas": projeto.pesquisas_realizadas,
            "custo_brl_ate_agora": projeto.custo_brl_ate_agora,
            "relatorio_id": projeto.relatorio_id,
            "updated_at": projeto.updated_at,
        },
        "mensagens": [
            {
                "id": m["id"],
                "role": m["role"],
                "content": m["content"],
                "tool_calls": m.get("tool_calls"),
                "citacoes": unpack_citacoes_from_msg(m),
                "agente": id_publico(m.get("agente")),
                "created_at": m["created_at"],
            }
            for m in mensagens
        ],
    }


# ─── POST /api/consultor/projetos/{projeto_id}/relatorio ─────────────────────

@router_consultor.post("/projetos/{projeto_id}/relatorio")
async def gerar_relatorio(
    projeto_id: str,
    body: RelatorioInput,
    request: Request,
):
    """
    Dispara geração do Relatório Formal (pipeline A0-A9 via RedisQueue).
    Responde imediatamente com relatorio_id; pipeline roda assíncrono.
    Frontend faz polling em GET /projetos/{id} para checar status.
    """
    user_id = _auth_user_id(request)
    try:
        projeto = await carregar_projeto(projeto_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if not (projeto.localizacao or {}).get("cidade"):
        raise HTTPException(
            status_code=400,
            detail="Projeto sem localização definida. Informe cidade e bairro primeiro.",
        )

    # Disparo determinístico do pipeline (P-005): decisão de negócio do backend,
    # não uma tool que o Gemini pode ou não escolher chamar.
    resultado = await disparar_relatorio_formal(projeto_id, user_id)

    relatorio_id = resultado.get("relatorio_id")
    return {
        "relatorio_id": relatorio_id,
        "status": "CONSOLIDANDO",
        "mensagem": (
            "Estou montando seu Relatório Formal de Viabilidade. "
            "O processo leva de 3 a 5 minutos. "
            "Assim que estiver pronto, o link aparecerá aqui."
        ),
        "link_acompanhamento": f"/relatorios/{relatorio_id}/aguardando" if relatorio_id else None,
    }


# ─── PATCH /api/consultor/projetos/{projeto_id}/arquivar ─────────────────────

@router_consultor.patch("/projetos/{projeto_id}/arquivar")
async def arquivar(
    projeto_id: str,
    request: Request,
):
    """Soft delete: seta deleted_at. Projeto desaparece da lista mas nunca é apagado."""
    user_id = _auth_user_id(request)
    try:
        await arquivar_projeto(projeto_id, user_id)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Montado em api.py via:
#   from backend.routers.consultor import router_consultor
#   app.include_router(router_consultor)
