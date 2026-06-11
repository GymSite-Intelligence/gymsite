"""
Router /api/execucao — Playbook de Abertura (Fase 1).

Endpoints do usuário autenticado (JWT Supabase). Cliente service-role +
filtro por user_id no nível mais baixo (espelha as policies RLS).
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from supabase import create_client

from backend.services.execucao.playbook_generator import gerar_playbook_para_relatorio
from backend.services.execucao import playbook_service

router = APIRouter(prefix="/api/execucao", tags=["Execução — Playbook"])


def _sb():
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise HTTPException(status_code=500, detail="Supabase não configurado")
    return create_client(url, key)


def _require_user(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    try:
        user_res = _sb().auth.get_user(token)
        user = user_res.user
    except Exception:
        user = None
    if not user:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    return user.id


class GerarPlaybookRequest(BaseModel):
    relatorio_id: str = Field(..., min_length=10)
    force: bool = False


class AtualizarTarefaRequest(BaseModel):
    status: str = Field(..., description="A_FAZER|EM_ANDAMENTO|CONCLUIDA|BLOQUEADA|CANCELADA")
    custo_real: Optional[int] = Field(None, ge=0, description="Centavos")


class ChecklistRequest(BaseModel):
    concluido: bool


@router.post("/playbooks/gerar", status_code=201)
def gerar_playbook(data: GerarPlaybookRequest, request: Request):
    """Gera o Plano de Abertura a partir de um relatório concluído."""
    user_id = _require_user(request)
    sb = _sb()

    rel = (
        sb.table("relatorios")
        .select("user_id, org_id")
        .eq("id", data.relatorio_id)
        .is_("deleted_at", "null")
        .maybe_single()
        .execute()
    )
    if not rel or not rel.data:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    if rel.data.get("user_id") and rel.data["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Este relatório pertence a outra conta")

    try:
        resultado = gerar_playbook_para_relatorio(
            sb, data.relatorio_id, user_id=user_id, force=data.force
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return resultado


@router.get("/playbooks")
def listar_playbooks(request: Request):
    user_id = _require_user(request)
    return {"items": playbook_service.listar_playbooks(_sb(), user_id)}


@router.get("/playbooks/{playbook_id}")
def obter_playbook(playbook_id: str, request: Request):
    user_id = _require_user(request)
    pb = playbook_service.obter_playbook_completo(_sb(), playbook_id, user_id)
    if not pb:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    return pb


@router.patch("/tarefas/{tarefa_id}")
def atualizar_tarefa(tarefa_id: str, data: AtualizarTarefaRequest, request: Request):
    user_id = _require_user(request)
    try:
        return playbook_service.atualizar_status_tarefa(
            _sb(), tarefa_id, user_id, data.status, custo_real=data.custo_real
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/checklist/{item_id}")
def marcar_checklist(item_id: str, data: ChecklistRequest, request: Request):
    user_id = _require_user(request)
    try:
        return playbook_service.marcar_checklist_item(_sb(), item_id, user_id, data.concluido)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
