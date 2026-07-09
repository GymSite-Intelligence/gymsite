"""GET /api/cno/obras — busca obras EM CURSO do CNO por UF + município (+ bairro).

Read-only, exige login (ferramenta interna de teste; não é do produto do dono).
Fonte: cno_obras_grande_porte (proxy residencial minerado do basedosdados/RFB CNO —
área grande, situação em curso, exclui fitness/comercial). Cidade = id_municipio (IBGE),
que o front resolve pelo dataset estático MUNICIPIOS_BRASIL.
"""
from __future__ import annotations

from fastapi import APIRouter, Query, Request

from backend.routers.consultor import _auth_user_id
from tools.db_schema import tbl

router_cno = APIRouter(prefix="/api/cno", tags=["cno-obras"])

# Colunas úteis (ver análise: nome, área, endereço, bairro, datas, situação, id).
_COLS = (
    "id_cno,nome,area_m2,tipo_logradouro,logradouro,numero_logradouro,bairro,"
    "sigla_uf,id_municipio,cep,situacao,em_curso,data_inicio,data_situacao"
)
# Sinal residencial POSITIVO no nome (a tabela já exclui comercial; isto afina).
_RES_OR = (
    "nome.ilike.%residencial%,nome.ilike.%edific%,nome.ilike.%condominio%,"
    "nome.ilike.%incorporac%,nome.ilike.%empreendimento%"
)


@router_cno.get("/obras")
async def buscar_obras(
    request: Request,
    uf: str = Query(..., min_length=2, max_length=2),
    municipio_id: int | None = Query(None, description="id IBGE do município"),
    bairro: str | None = Query(None, max_length=80),
    residencial: bool = Query(True, description="filtra nomes com sinal residencial"),
    limit: int = Query(200, ge=1, le=500),
) -> dict:
    _auth_user_id(request)  # tela interna: exige usuário logado
    from api import _supabase_client

    sb = _supabase_client()
    q = (
        tbl(sb, "cno_obras_grande_porte")
        .select(_COLS, count="exact")
        .eq("em_curso", True)
        .eq("sigla_uf", uf.upper())
    )
    if municipio_id:
        q = q.eq("id_municipio", municipio_id)
    if bairro:
        q = q.ilike("bairro", f"%{bairro}%")
    if residencial:
        q = q.or_(_RES_OR)
    r = q.order("data_inicio", desc=True).limit(limit).execute()
    return {"total": r.count, "obras": r.data or []}
