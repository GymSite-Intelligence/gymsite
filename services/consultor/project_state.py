"""
services/consultor/project_state.py
=====================================
CRUD de UserProject no Supabase.

Tabela: user_projects (criada pela migration 20260620_add_user_projects.sql)
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from supabase import create_client, Client

from tools.db_schema import tbl, rpc

_supabase: Client | None = None

def _client() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_ROLE_KEY"],
        )
    return _supabase


@dataclass
class ProjectState:
    id: str
    user_id: str
    status: str = "EM_CONVERSA"
    intencao_principal: str | None = None
    localizacao: dict = field(default_factory=dict)
    modelo_negocio: dict = field(default_factory=dict)
    concorrencia: dict = field(default_factory=dict)
    mercado: dict = field(default_factory=dict)
    candidatos: dict = field(default_factory=dict)
    financeiro: dict = field(default_factory=dict)
    posicionamento: dict = field(default_factory=dict)
    anexos: list = field(default_factory=list)
    acoes: list = field(default_factory=list)
    pesquisas_realizadas: dict = field(default_factory=dict)
    custo_brl_ate_agora: float = 0.0
    relatorio_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


def _row_to_state(row: dict) -> ProjectState:
    return ProjectState(
        id=row["id"],
        user_id=row["user_id"],
        status=row.get("status", "EM_CONVERSA"),
        intencao_principal=row.get("intencao_principal"),
        localizacao=row.get("localizacao") or {},
        modelo_negocio=row.get("modelo_negocio") or {},
        concorrencia=row.get("concorrencia") or {},
        mercado=row.get("mercado") or {},
        candidatos=row.get("candidatos") or {},
        financeiro=row.get("financeiro") or {},
        posicionamento=row.get("posicionamento") or {},
        anexos=row.get("anexos") or [],
        acoes=row.get("acoes") or [],
        pesquisas_realizadas=row.get("pesquisas_realizadas") or {},
        custo_brl_ate_agora=float(row.get("custo_brl_ate_agora") or 0.0),
        relatorio_id=row.get("relatorio_id"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


async def criar_projeto(user_id: str, intencao: str | None = None) -> ProjectState:
    """Cria um novo UserProject para o usuário."""
    import asyncio
    db = _client()
    data = {
        "user_id": user_id,
        "status": "EM_CONVERSA",
        "intencao_principal": intencao,
        "localizacao": {},
        "modelo_negocio": {},
        "concorrencia": {},
        "mercado": {},
        "candidatos": {},
        "financeiro": {},
        "posicionamento": {},
        "anexos": [],
        "acoes": [],
        "pesquisas_realizadas": {
            "mercado": False,
            "concorrentes": False,
            "reviews": False,
            "oferta_concorrentes": False,
            "demografia": False,
            "pontos_comerciais": False,
            "investimento": False,
        },
        "custo_brl_ate_agora": 0.0,
    }
    result = await asyncio.to_thread(
        lambda: tbl(db, "user_projects").insert(data).execute()
    )
    return _row_to_state(result.data[0])


async def carregar_projeto(projeto_id: str, user_id: str) -> ProjectState:
    """Carrega um UserProject pelo ID. Valida que pertence ao user_id."""
    import asyncio
    db = _client()
    result = await asyncio.to_thread(
        lambda: tbl(db, "user_projects")
            .select("*")
            .eq("id", projeto_id)
            .eq("user_id", user_id)
            .is_("deleted_at", "null")
            .single()
            .execute()
    )
    if not result.data:
        raise ValueError(f"Projeto {projeto_id} não encontrado para o usuário.")
    return _row_to_state(result.data)


async def listar_projetos(user_id: str) -> list[ProjectState]:
    """Lista projetos ativos do usuário, ordenados por updated_at desc."""
    import asyncio
    db = _client()
    result = await asyncio.to_thread(
        lambda: tbl(db, "user_projects")
            .select("id,user_id,status,intencao_principal,localizacao,modelo_negocio,pesquisas_realizadas,custo_brl_ate_agora,relatorio_id,created_at,updated_at")
            .eq("user_id", user_id)
            .is_("deleted_at", "null")
            .order("updated_at", desc=True)
            .limit(20)
            .execute()
    )
    return [_row_to_state(r) for r in (result.data or [])]


async def atualizar_campo_projeto(
    projeto_id: str,
    campo: str,
    valor: Any,
    user_id: str | None = None,
) -> None:
    """
    Atualiza um campo JSONB do UserProject.
    Para campos aninhados (localizacao.cidade), usar atualizar_localizacao().

    user_id: quando informado, restringe o UPDATE ao dono (defense-in-depth — o
    client roda com SERVICE_ROLE_KEY, que BYPASSA o RLS, então a única barreira
    é este filtro explícito). Sempre passe projeto.user_id a partir do engine.
    """
    import asyncio
    db = _client()

    def _run():
        q = (tbl(db, "user_projects")
               .update({campo: valor, "updated_at": datetime.now(timezone.utc).isoformat()})
               .eq("id", projeto_id))
        if user_id is not None:
            q = q.eq("user_id", user_id)
        return q.execute()

    await asyncio.to_thread(_run)


async def marcar_pesquisa_realizada(
    projeto_id: str,
    pesquisa: str,
    user_id: str | None = None,
) -> None:
    """
    Marca uma pesquisa como realizada no JSONB pesquisas_realizadas.
    pesquisa: 'mercado' | 'concorrentes' | 'reviews' | 'oferta_concorrentes'
              | 'demografia' | 'pontos_comerciais' | 'investimento'

    Usa a RPC `marcar_pesquisa` (merge atômico `|| jsonb_build_object` num único
    UPDATE) — elimina o lost-update do antigo read-modify-write quando as tools
    de um turno rodam em paralelo (asyncio.gather no engine).
    """
    import asyncio
    db = _client()
    await asyncio.to_thread(
        lambda: rpc(db, "marcar_pesquisa", {
            "p_projeto_id": projeto_id,
            "p_pesquisa": pesquisa,
            "p_user_id": user_id,
        }).execute()
    )


async def atualizar_status(projeto_id: str, status: str) -> None:
    """Atualiza status do projeto: EM_CONVERSA | PESQUISANDO | CONSOLIDANDO | RELATORIO_GERADO | ARQUIVADO"""
    await atualizar_campo_projeto(projeto_id, "status", status)


async def arquivar_projeto(projeto_id: str, user_id: str) -> None:
    """Soft delete: seta deleted_at. Nunca apaga dados."""
    import asyncio
    db = _client()
    await asyncio.to_thread(
        lambda: tbl(db, "user_projects")
            .update({
                "deleted_at": datetime.now(timezone.utc).isoformat(),
                "status": "ARQUIVADO",
            })
            .eq("id", projeto_id)
            .eq("user_id", user_id)
            .execute()
    )
