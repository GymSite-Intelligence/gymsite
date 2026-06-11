"""
Router Admin — Parceiros (Fornecedores Curados)

Endpoints para cadastro, curadoria e gestão de parceiros.
Acesso restrito a admins da plataforma: JWT Supabase válido + (user_metadata.role
em {admin, superadmin} OU email presente em ADMIN_EMAILS do ambiente).
Valores monetários (lead_valor, valor_mensalidade) em centavos (int).
"""

import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, validator
from supabase import create_client
from typing import Optional
from uuid import UUID

from backend.services.execucao.parceiro_service import (
    ParceiroService,
    ParceiroCreate,
    ParceiroUpdate,
    CATEGORIAS_VALIDAS,
    TIPOS_PARCERIA_VALIDOS,
    STATUS_VALIDOS,
)

router = APIRouter(prefix="/api/admin/parceiros", tags=["Admin — Parceiros"])


def _sb():
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise HTTPException(status_code=500, detail="Supabase não configurado")
    return create_client(url, key)


def get_service() -> ParceiroService:
    return ParceiroService(_sb())


def require_admin(request: Request) -> dict:
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

    role = (user.user_metadata or {}).get("role", "")
    admins = {
        e.strip().lower()
        for e in os.getenv("ADMIN_EMAILS", "").split(",")
        if e.strip()
    }
    email = (user.email or "").lower()
    if role not in ("admin", "superadmin") and email not in admins:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")

    return {"user_id": user.id, "email": email, "role": role or "admin"}


# =============================================================================
# Schemas Pydantic
# =============================================================================

class ParceiroCreateRequest(BaseModel):
    nome: str = Field(..., min_length=2, max_length=200)
    descricao: Optional[str] = Field(None, max_length=2000)
    logo_url: Optional[str] = Field(None, max_length=500)
    site_url: Optional[str] = Field(None, max_length=500)
    telefone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=200)
    categorias: list[str] = Field(default_factory=list)
    ufs_atuacao: list[str] = Field(default_factory=list)
    cidades_atuacao: list[str] = Field(default_factory=list)
    tipo_parceria: str = Field(default="LEAD_GENERATION")
    lead_valor: Optional[int] = Field(None, ge=0, description="Centavos")
    lead_maximo_mes: Optional[int] = Field(None, ge=1)
    comissao_percentual: Optional[float] = Field(None, ge=0, le=100)
    valor_mensalidade: Optional[int] = Field(None, ge=0, description="Centavos")
    desconto_oferecido: Optional[str] = Field(None, max_length=200)
    desconto_codigo: Optional[str] = Field(None, max_length=100)
    diferenciais: list[str] = Field(default_factory=list)

    @validator("categorias")
    def validar_categorias(cls, v):
        invalidas = set(v) - CATEGORIAS_VALIDAS
        if invalidas:
            raise ValueError(f"Categorias inválidas: {invalidas}")
        return v

    @validator("tipo_parceria")
    def validar_tipo(cls, v):
        if v not in TIPOS_PARCERIA_VALIDOS:
            raise ValueError(f"Tipo deve ser um de: {TIPOS_PARCERIA_VALIDOS}")
        return v


class ParceiroUpdateRequest(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=200)
    descricao: Optional[str] = Field(None, max_length=2000)
    logo_url: Optional[str] = Field(None, max_length=500)
    site_url: Optional[str] = Field(None, max_length=500)
    telefone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=200)
    categorias: Optional[list[str]] = None
    ufs_atuacao: Optional[list[str]] = None
    cidades_atuacao: Optional[list[str]] = None
    tipo_parceria: Optional[str] = None
    lead_valor: Optional[int] = Field(None, ge=0, description="Centavos")
    lead_maximo_mes: Optional[int] = Field(None, ge=1)
    comissao_percentual: Optional[float] = Field(None, ge=0, le=100)
    valor_mensalidade: Optional[int] = Field(None, ge=0, description="Centavos")
    desconto_oferecido: Optional[str] = Field(None, max_length=200)
    desconto_codigo: Optional[str] = Field(None, max_length=100)
    diferenciais: Optional[list[str]] = None
    status: Optional[str] = None
    curadoria_nota: Optional[int] = Field(None, ge=1, le=5)
    curadoria_observacao: Optional[str] = Field(None, max_length=2000)

    @validator("categorias")
    def validar_categorias(cls, v):
        if v is None:
            return v
        invalidas = set(v) - CATEGORIAS_VALIDAS
        if invalidas:
            raise ValueError(f"Categorias inválidas: {invalidas}")
        return v

    @validator("tipo_parceria")
    def validar_tipo(cls, v):
        if v is None:
            return v
        if v not in TIPOS_PARCERIA_VALIDOS:
            raise ValueError(f"Tipo deve ser um de: {TIPOS_PARCERIA_VALIDOS}")
        return v

    @validator("status")
    def validar_status(cls, v):
        if v is None:
            return v
        if v not in STATUS_VALIDOS:
            raise ValueError(f"Status deve ser um de: {STATUS_VALIDOS}")
        return v


# =============================================================================
# Endpoints
# =============================================================================

@router.post("", status_code=201)
def criar_parceiro(
    data: ParceiroCreateRequest,
    admin=Depends(require_admin),
    service: ParceiroService = Depends(get_service),
):
    """Criar novo parceiro (status inicial: PENDENTE)."""
    try:
        parceiro = service.criar(
            ParceiroCreate(**data.dict()),
            curador_id=admin["user_id"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return dict(parceiro.__dict__)


@router.get("")
def listar_parceiros(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoria"),
    uf: Optional[str] = Query(None, description="Filtrar por UF"),
    tipo_parceria: Optional[str] = Query(None, description="Filtrar por tipo"),
    busca: Optional[str] = Query(None, description="Buscar por nome/descrição"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin=Depends(require_admin),
    service: ParceiroService = Depends(get_service),
):
    """Listar parceiros com filtros e paginação."""
    items, total = service.listar(
        status=status,
        categoria=categoria,
        uf=uf,
        tipo_parceria=tipo_parceria,
        busca=busca,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [dict(i.__dict__) for i in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/publico/para-tarefa")
def parceiros_para_tarefa(
    categoria: str = Query(..., description="Categoria da tarefa"),
    uf: Optional[str] = Query(None),
    cidade: Optional[str] = Query(None),
    service: ParceiroService = Depends(get_service),
):
    """Sugestão de parceiros para uma tarefa do playbook (não exige admin)."""
    if categoria not in CATEGORIAS_VALIDAS:
        raise HTTPException(status_code=400, detail=f"Categoria inválida. Use: {CATEGORIAS_VALIDAS}")

    parceiros = service.buscar_para_tarefa(categoria=categoria, uf=uf, cidade=cidade, limite=3)
    return {
        "parceiros": [dict(p.__dict__) for p in parceiros],
        "categoria": categoria,
    }


@router.get("/{parceiro_id}")
def obter_parceiro(
    parceiro_id: UUID,
    admin=Depends(require_admin),
    service: ParceiroService = Depends(get_service),
):
    """Obter detalhes de um parceiro."""
    parceiro = service.obter(parceiro_id)
    if not parceiro:
        raise HTTPException(status_code=404, detail="Parceiro não encontrado")
    return dict(parceiro.__dict__)


@router.patch("/{parceiro_id}")
def atualizar_parceiro(
    parceiro_id: UUID,
    data: ParceiroUpdateRequest,
    admin=Depends(require_admin),
    service: ParceiroService = Depends(get_service),
):
    """Atualizar parceiro (incluindo curadoria)."""
    try:
        parceiro = service.atualizar(
            parceiro_id,
            ParceiroUpdate(**data.dict(exclude_unset=True)),
            curador_id=admin["user_id"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not parceiro:
        raise HTTPException(status_code=404, detail="Parceiro não encontrado")
    return dict(parceiro.__dict__)


@router.delete("/{parceiro_id}", status_code=204)
def excluir_parceiro(
    parceiro_id: UUID,
    admin=Depends(require_admin),
    service: ParceiroService = Depends(get_service),
):
    """Excluir parceiro (soft delete)."""
    ok = service.excluir(parceiro_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Parceiro não encontrado")
    return None


@router.post("/{parceiro_id}/curadoria")
def aprovar_parceiro(
    parceiro_id: UUID,
    nota: int = Query(..., ge=1, le=5),
    observacao: Optional[str] = Query(None),
    admin=Depends(require_admin),
    service: ParceiroService = Depends(get_service),
):
    """Aprovar parceiro após curadoria."""
    parceiro = service.atualizar(
        parceiro_id,
        ParceiroUpdate(
            status="ATIVO",
            curadoria_nota=nota,
            curadoria_observacao=observacao,
        ),
        curador_id=admin["user_id"],
    )
    if not parceiro:
        raise HTTPException(status_code=404, detail="Parceiro não encontrado")
    return dict(parceiro.__dict__)
