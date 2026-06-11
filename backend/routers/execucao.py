"""
Router /api/execucao — Playbook de Abertura (Fase 1).

Endpoints do usuário autenticado (JWT Supabase). Cliente service-role +
filtro por user_id no nível mais baixo (espelha as policies RLS).
"""
from __future__ import annotations

import os
import re
import uuid
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from supabase import create_client

from backend.services.execucao.playbook_generator import (
    gerar_playbook_para_relatorio,
    semear_okrs_para_playbook,
)
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


class NotaRequest(BaseModel):
    texto: str = Field(..., min_length=1, max_length=4000)


class PessoaRequest(BaseModel):
    nome: str = Field(..., min_length=1, max_length=120)
    papel: Optional[str] = Field(None, max_length=80)
    email: Optional[str] = Field(None, max_length=200)
    telefone: Optional[str] = Field(None, max_length=40)


class PessoaPatchRequest(BaseModel):
    nome: Optional[str] = Field(None, max_length=120)
    papel: Optional[str] = Field(None, max_length=80)
    email: Optional[str] = Field(None, max_length=200)
    telefone: Optional[str] = Field(None, max_length=40)


class AtribuirRequest(BaseModel):
    pessoa_id: Optional[str] = None


class OkrPatchRequest(BaseModel):
    objetivo: Optional[str] = Field(None, max_length=200)
    descricao: Optional[str] = Field(None, max_length=500)
    kr1_descricao: Optional[str] = Field(None, max_length=200)
    kr2_descricao: Optional[str] = Field(None, max_length=200)
    kr3_descricao: Optional[str] = Field(None, max_length=200)
    kr1_target: Optional[float] = Field(None, ge=0)
    kr2_target: Optional[float] = Field(None, ge=0)
    kr3_target: Optional[float] = Field(None, ge=0)
    kr1_atual: Optional[float] = Field(None, ge=0)
    kr2_atual: Optional[float] = Field(None, ge=0)
    kr3_atual: Optional[float] = Field(None, ge=0)
    status: Optional[str] = None


class OkrCreateRequest(BaseModel):
    objetivo: str = Field(..., min_length=1, max_length=200)
    descricao: Optional[str] = Field(None, max_length=500)
    kr1_descricao: Optional[str] = Field(None, max_length=200)
    kr1_target: Optional[float] = Field(None, ge=0)
    kr2_descricao: Optional[str] = Field(None, max_length=200)
    kr2_target: Optional[float] = Field(None, ge=0)
    kr3_descricao: Optional[str] = Field(None, max_length=200)
    kr3_target: Optional[float] = Field(None, ge=0)


class TarefaCreateRequest(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=200)
    descricao: Optional[str] = Field(None, max_length=2000)
    categoria: str = "OUTRO"
    custo_planejado: Optional[int] = Field(None, ge=0, description="Centavos")
    data_inicio: Optional[str] = None
    data_prevista_conclusao: Optional[str] = None
    responsavel_nome: Optional[str] = Field(None, max_length=120)


class TarefaEditRequest(BaseModel):
    titulo: Optional[str] = Field(None, max_length=200)
    descricao: Optional[str] = Field(None, max_length=2000)
    categoria: Optional[str] = None
    custo_planejado: Optional[int] = Field(None, ge=0, description="Centavos")
    data_inicio: Optional[str] = None
    data_prevista_conclusao: Optional[str] = None
    responsavel_nome: Optional[str] = Field(None, max_length=120)


class ChecklistCreateRequest(BaseModel):
    descricao: str = Field(..., min_length=1, max_length=300)


ANEXO_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
ANEXO_TIPOS = {
    "application/pdf", "image/png", "image/jpeg", "image/webp", "image/heic",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


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


@router.get("/tarefas/{tarefa_id}/notas")
def listar_notas(tarefa_id: str, request: Request):
    user_id = _require_user(request)
    try:
        return {"items": playbook_service.listar_notas(_sb(), tarefa_id, user_id)}
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/tarefas/{tarefa_id}/notas", status_code=201)
def adicionar_nota(tarefa_id: str, data: NotaRequest, request: Request):
    user_id = _require_user(request)
    sb = _sb()
    try:
        user_res = sb.auth.get_user(request.headers.get("authorization", "").removeprefix("Bearer ").strip())
        meta = (user_res.user.user_metadata or {}) if user_res and user_res.user else {}
        autor = meta.get("full_name") or meta.get("name") or "Você"
    except Exception:
        autor = "Você"
    try:
        return playbook_service.adicionar_nota(sb, tarefa_id, user_id, data.texto, autor_nome=autor)
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


# ── CRUD de etapas ─────────────────────────────────────────────────────────
@router.post("/playbooks/{playbook_id}/tarefas", status_code=201)
def criar_tarefa(playbook_id: str, data: TarefaCreateRequest, request: Request):
    user_id = _require_user(request)
    try:
        return playbook_service.criar_tarefa(
            _sb(), playbook_id, user_id, data.model_dump(exclude_unset=True)
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/tarefas/{tarefa_id}/detalhes")
def editar_tarefa(tarefa_id: str, data: TarefaEditRequest, request: Request):
    user_id = _require_user(request)
    try:
        return playbook_service.editar_tarefa(
            _sb(), tarefa_id, user_id, data.model_dump(exclude_unset=True)
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/tarefas/{tarefa_id}", status_code=204)
def excluir_tarefa(tarefa_id: str, request: Request):
    user_id = _require_user(request)
    try:
        playbook_service.excluir_tarefa(_sb(), tarefa_id, user_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/tarefas/{tarefa_id}/checklist", status_code=201)
def adicionar_checklist(tarefa_id: str, data: ChecklistCreateRequest, request: Request):
    user_id = _require_user(request)
    try:
        return playbook_service.adicionar_checklist_item(_sb(), tarefa_id, user_id, data.descricao)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/checklist/{item_id}", status_code=204)
def excluir_checklist(item_id: str, request: Request):
    user_id = _require_user(request)
    try:
        playbook_service.excluir_checklist_item(_sb(), item_id, user_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Metas (OKRs) ───────────────────────────────────────────────────────────
@router.post("/playbooks/{playbook_id}/okrs", status_code=201)
def criar_okr(playbook_id: str, data: OkrCreateRequest, request: Request):
    user_id = _require_user(request)
    try:
        return playbook_service.criar_okr(
            _sb(), playbook_id, user_id, data.model_dump(exclude_unset=True)
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/okrs/{okr_id}", status_code=204)
def excluir_okr(okr_id: str, request: Request):
    user_id = _require_user(request)
    try:
        playbook_service.excluir_okr(_sb(), okr_id, user_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))



@router.post("/playbooks/{playbook_id}/okrs/gerar", status_code=201)
def gerar_okrs(playbook_id: str, request: Request):
    """Semeia metas num plano existente (planos criados antes da F2)."""
    user_id = _require_user(request)
    try:
        criados = semear_okrs_para_playbook(_sb(), playbook_id, user_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"okrs_criados": criados}


@router.patch("/okrs/{okr_id}")
def atualizar_okr(okr_id: str, data: OkrPatchRequest, request: Request):
    user_id = _require_user(request)
    try:
        return playbook_service.atualizar_okr(
            _sb(), okr_id, user_id, data.model_dump(exclude_unset=True)
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Pessoas do projeto ─────────────────────────────────────────────────────
@router.get("/projetos/{projeto_id}/pessoas")
def listar_pessoas(projeto_id: str, request: Request):
    user_id = _require_user(request)
    try:
        return {"items": playbook_service.listar_pessoas(_sb(), projeto_id, user_id)}
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/projetos/{projeto_id}/pessoas", status_code=201)
def criar_pessoa(projeto_id: str, data: PessoaRequest, request: Request):
    user_id = _require_user(request)
    try:
        return playbook_service.criar_pessoa(
            _sb(), projeto_id, user_id,
            nome=data.nome, papel=data.papel, email=data.email, telefone=data.telefone,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/pessoas/{pessoa_id}")
def atualizar_pessoa(pessoa_id: str, data: PessoaPatchRequest, request: Request):
    user_id = _require_user(request)
    try:
        return playbook_service.atualizar_pessoa(
            _sb(), pessoa_id, user_id, data.model_dump(exclude_unset=True)
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/pessoas/{pessoa_id}", status_code=204)
def remover_pessoa(pessoa_id: str, request: Request):
    user_id = _require_user(request)
    try:
        playbook_service.remover_pessoa(_sb(), pessoa_id, user_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


class CustoRealRequest(BaseModel):
    custo_real: int = Field(..., ge=0, description="Centavos")


@router.patch("/tarefas/{tarefa_id}/custo")
def registrar_custo(tarefa_id: str, data: CustoRealRequest, request: Request):
    user_id = _require_user(request)
    try:
        return playbook_service.registrar_custo_real(_sb(), tarefa_id, user_id, data.custo_real)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/tarefas/{tarefa_id}/responsavel")
def atribuir_responsavel_tarefa(tarefa_id: str, data: AtribuirRequest, request: Request):
    user_id = _require_user(request)
    try:
        return playbook_service.atribuir_responsavel_tarefa(_sb(), tarefa_id, user_id, data.pessoa_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/checklist/{item_id}/responsavel")
def atribuir_responsavel_checklist(item_id: str, data: AtribuirRequest, request: Request):
    user_id = _require_user(request)
    try:
        return playbook_service.atribuir_responsavel_checklist(_sb(), item_id, user_id, data.pessoa_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Anexos ─────────────────────────────────────────────────────────────────
@router.get("/tarefas/{tarefa_id}/anexos")
def listar_anexos(tarefa_id: str, request: Request):
    user_id = _require_user(request)
    try:
        return {"items": playbook_service.listar_anexos(_sb(), tarefa_id, user_id)}
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/tarefas/{tarefa_id}/anexos", status_code=201)
async def enviar_anexo(
    tarefa_id: str,
    request: Request,
    arquivo: UploadFile = File(...),
    nota_id: Optional[str] = Form(None),
):
    user_id = _require_user(request)
    sb = _sb()
    try:
        tarefa = playbook_service._tarefa_do_usuario(sb, tarefa_id, user_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))

    content_type = (arquivo.content_type or "").lower()
    if content_type not in ANEXO_TIPOS:
        raise HTTPException(
            status_code=400,
            detail="Tipo de arquivo não aceito. Envie PDF, imagem, Word ou Excel.",
        )
    conteudo = await arquivo.read()
    if len(conteudo) > ANEXO_MAX_BYTES:
        raise HTTPException(status_code=400, detail="Arquivo acima de 10 MB.")
    if not conteudo:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    nome_original = arquivo.filename or "arquivo"
    nome_seguro = re.sub(r"[^A-Za-z0-9._-]+", "_", nome_original)[-120:]
    storage_path = f"{tarefa['projeto_id']}/{tarefa_id}/{uuid.uuid4().hex}_{nome_seguro}"
    try:
        sb.storage.from_(playbook_service.BUCKET_ANEXOS).upload(
            storage_path, conteudo, {"content-type": content_type}
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Falha ao guardar o arquivo. Tente de novo.")

    return playbook_service.registrar_anexo(
        sb, tarefa_id, user_id,
        nome_arquivo=nome_original, storage_path=storage_path,
        content_type=content_type, tamanho_bytes=len(conteudo), nota_id=nota_id,
    )


@router.get("/anexos/{anexo_id}/download")
def baixar_anexo(anexo_id: str, request: Request):
    user_id = _require_user(request)
    try:
        return {"url": playbook_service.url_download_anexo(_sb(), anexo_id, user_id)}
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.delete("/anexos/{anexo_id}", status_code=204)
def excluir_anexo(anexo_id: str, request: Request):
    user_id = _require_user(request)
    try:
        playbook_service.remover_anexo(_sb(), anexo_id, user_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
