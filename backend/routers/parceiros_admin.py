"""
Router Admin — Parceiros (Fornecedores Curados)

Endpoints para cadastro, curadoria e gestão de parceiros.
Acesso restrito a admins da plataforma.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator
from typing import Optional
from uuid import UUID

from services.execucao.parceiro_service import (
    ParceiroService,
    ParceiroCreate,
    ParceiroUpdate,
    CATEGORIAS_VALIDAS,
    TIPOS_PARCERIA_VALIDOS,
    STATUS_VALIDOS,
)

router = APIRouter(prefix="/api/admin/parceiros", tags=["Admin — Parceiros"])


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
    lead_valor: Optional[float] = Field(None, ge=0)
    lead_maximo_mes: Optional[int] = Field(None, ge=1)
    comissao_percentual: Optional[float] = Field(None, ge=0, le=100)
    valor_mensalidade: Optional[float] = Field(None, ge=0)
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
    lead_valor: Optional[float] = Field(None, ge=0)
    lead_maximo_mes: Optional[int] = Field(None, ge=1)
    comissao_percentual: Optional[float] = Field(None, ge=0, le=100)
    valor_mensalidade: Optional[float] = Field(None, ge=0)
    desconto_oferecido: Optional[str] = Field(None, max_length=200)
    desconto_codigo: Optional[str] = Field(None, max_length=100)
    diferenciais: Optional[list[str]] = None
    status: Optional[str] = Field(None)
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


class ParceiroListResponse(BaseModel):
    items: list[dict]
    total: int
    limit: int
    offset: int


# =============================================================================
# Dependências
# =============================================================================

# TODO: Implementar autenticação admin real
# Por enquanto, placeholder para depender de um usuário autenticado
async def require_admin():
    """Middleware que verifica se o usuário é admin da plataforma."""
    # Implementar: verificar JWT + role == 'admin' ou 'superadmin'
    # Por enquanto, retorna um user_id mock para desenvolvimento
    return {"user_id": "admin-mock", "role": "admin"}


# =============================================================================
# Endpoints
# =============================================================================

@router.post("", status_code=201)
async def criar_parceiro(
    data: ParceiroCreateRequest,
    admin=Depends(require_admin),
    db=None,  # TODO: injetar dependência real do banco
):
    """Criar novo parceiro (status inicial: PENDENTE)."""
    service = ParceiroService(db)
    parceiro = await service.criar(
        ParceiroCreate(**data.dict()),
        curador_id=admin.get("user_id")
    )
    return parceiro


@router.get("")
async def listar_parceiros(
    status: Optional[str] = Query(None, description="Filtrar por status"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoria"),
    uf: Optional[str] = Query(None, description="Filtrar por UF"),
    tipo_parceria: Optional[str] = Query(None, description="Filtrar por tipo"),
    busca: Optional[str] = Query(None, description="Buscar por nome/descrição"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin=Depends(require_admin),
    db=None,
):
    """Listar parceiros com filtros e paginação."""
    service = ParceiroService(db)
    items, total = await service.listar(
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


@router.get("/{parceiro_id}")
async def obter_parceiro(
    parceiro_id: UUID,
    admin=Depends(require_admin),
    db=None,
):
    """Obter detalhes de um parceiro."""
    service = ParceiroService(db)
    parceiro = await service.obter(parceiro_id)
    if not parceiro:
        raise HTTPException(status_code=404, detail="Parceiro não encontrado")
    return dict(parceiro.__dict__)


@router.patch("/{parceiro_id}")
async def atualizar_parceiro(
    parceiro_id: UUID,
    data: ParceiroUpdateRequest,
    admin=Depends(require_admin),
    db=None,
):
    """Atualizar parceiro (incluindo curadoria)."""
    service = ParceiroService(db)
    parceiro = await service.atualizar(
        parceiro_id,
        ParceiroUpdate(**data.dict(exclude_unset=True)),
        curador_id=admin.get("user_id")
    )
    if not parceiro:
        raise HTTPException(status_code=404, detail="Parceiro não encontrado")
    return dict(parceiro.__dict__)


@router.delete("/{parceiro_id}", status_code=204)
async def excluir_parceiro(
    parceiro_id: UUID,
    admin=Depends(require_admin),
    db=None,
):
    """Excluir parceiro (soft delete)."""
    service = ParceiroService(db)
    ok = await service.excluir(parceiro_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Parceiro não encontrado")
    return None


@router.post("/{parceiro_id}/curadoria")
async def aprovar_parceiro(
    parceiro_id: UUID,
    nota: int = Query(..., ge=1, le=5),
    observacao: Optional[str] = Query(None),
    admin=Depends(require_admin),
    db=None,
):
    """Aprovar parceiro após curadoria."""
    service = ParceiroService(db)
    parceiro = await service.atualizar(
        parceiro_id,
        ParceiroUpdate(
            status="ATIVO",
            curadoria_nota=nota,
            curadoria_observacao=observacao,
        ),
        curador_id=admin.get("user_id")
    )
    if not parceiro:
        raise HTTPException(status_code=404, detail="Parceiro não encontrado")
    return dict(parceiro.__dict__)


# =============================================================================
# Endpoints Públicos (para o Playbook)
# =============================================================================

@router.get("/publico/para-tarefa")
async def parceiros_para_tarefa(
    categoria: str = Query(..., description="Categoria da tarefa"),
    uf: Optional[str] = Query(None),
    cidade: Optional[str] = Query(None),
    db=None,
):
    """
    Endpoint público (não requer admin) para sugerir parceiros
    em uma tarefa específica do playbook.
    """
    if categoria not in CATEGORIAS_VALIDAS:
        raise HTTPException(status_code=400, detail=f"Categoria inválida. Use: {CATEGORIAS_VALIDAS}")

    service = ParceiroService(db)
    parceiros = await service.buscar_para_tarefa(
        categoria=categoria,
        uf=uf,
        cidade=cidade,
        limite=3
    )
    return {
        "parceiros": [dict(p.__dict__) for p in parceiros],
        "categoria": categoria,
    }
