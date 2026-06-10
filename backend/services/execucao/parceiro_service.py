"""
Parceiro Service — CRUD de fornecedores curados para o playbook.

Acesso admin para cadastro, curadoria e gestão de parceiros.
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID
import json


@dataclass
class ParceiroCreate:
    nome: str
    descricao: Optional[str] = None
    logo_url: Optional[str] = None
    site_url: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    categorias: list[str] = None
    ufs_atuacao: list[str] = None
    cidades_atuacao: list[str] = None
    tipo_parceria: str = "LEAD_GENERATION"
    lead_valor: Optional[float] = None
    lead_maximo_mes: Optional[int] = None
    comissao_percentual: Optional[float] = None
    valor_mensalidade: Optional[float] = None
    desconto_oferecido: Optional[str] = None
    desconto_codigo: Optional[str] = None
    diferenciais: list[str] = None


@dataclass
class ParceiroUpdate:
    nome: Optional[str] = None
    descricao: Optional[str] = None
    logo_url: Optional[str] = None
    site_url: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    categorias: Optional[list[str]] = None
    ufs_atuacao: Optional[list[str]] = None
    cidades_atuacao: Optional[list[str]] = None
    tipo_parceria: Optional[str] = None
    lead_valor: Optional[float] = None
    lead_maximo_mes: Optional[int] = None
    comissao_percentual: Optional[float] = None
    valor_mensalidade: Optional[float] = None
    desconto_oferecido: Optional[str] = None
    desconto_codigo: Optional[str] = None
    diferenciais: Optional[list[str]] = None
    status: Optional[str] = None
    curadoria_nota: Optional[int] = None
    curadoria_observacao: Optional[str] = None


@dataclass
class ParceiroOut:
    id: UUID
    nome: str
    descricao: Optional[str]
    logo_url: Optional[str]
    site_url: Optional[str]
    telefone: Optional[str]
    email: Optional[str]
    categorias: list[str]
    ufs_atuacao: list[str]
    cidades_atuacao: list[str]
    tipo_parceria: str
    lead_valor: Optional[float]
    lead_maximo_mes: Optional[int]
    comissao_percentual: Optional[float]
    valor_mensalidade: Optional[float]
    desconto_oferecido: Optional[str]
    desconto_codigo: Optional[str]
    diferenciais: list[str]
    status: str
    curadoria_nota: Optional[int]
    curadoria_observacao: Optional[str]
    leads_gerados: int
    leads_convertidos: int
    rating_medio: float
    created_at: str


# Categorias válidas (mesmas do playbook)
CATEGORIAS_VALIDAS = {
    "IMOBILIARIO", "LEGAL", "OBRAS", "EQUIPAMENTOS",
    "TECNOLOGIA", "RH", "MARKETING", "FINANCEIRO", "OPERACIONAL", "OUTRO"
}

TIPOS_PARCERIA_VALIDOS = {"LEAD_GENERATION", "AFILIADO", "SPONSORED", "WHITE_LABEL"}
STATUS_VALIDOS = {"PENDENTE", "ATIVO", "PAUSADO", "CANCELADO", "REPROVADO"}


def _validar_categorias(categorias: list[str]) -> None:
    invalidas = set(categorias or []) - CATEGORIAS_VALIDAS
    if invalidas:
        raise ValueError(f"Categorias inválidas: {invalidas}")


def _row_to_parceiro_out(row: dict) -> ParceiroOut:
    return ParceiroOut(
        id=row["id"],
        nome=row["nome"],
        descricao=row.get("descricao"),
        logo_url=row.get("logo_url"),
        site_url=row.get("site_url"),
        telefone=row.get("telefone"),
        email=row.get("email"),
        categorias=row.get("categorias") or [],
        ufs_atuacao=row.get("ufs_atuacao") or [],
        cidades_atuacao=row.get("cidades_atuacao") or [],
        tipo_parceria=row["tipo_parceria"],
        lead_valor=row.get("lead_valor"),
        lead_maximo_mes=row.get("lead_maximo_mes"),
        comissao_percentual=row.get("comissao_percentual"),
        valor_mensalidade=row.get("valor_mensalidade"),
        desconto_oferecido=row.get("desconto_oferecido"),
        desconto_codigo=row.get("desconto_codigo"),
        diferenciais=row.get("diferenciais") or [],
        status=row["status"],
        curadoria_nota=row.get("curadoria_nota"),
        curadoria_observacao=row.get("curadoria_observacao"),
        leads_gerados=row.get("leads_gerados", 0),
        leads_convertidos=row.get("leads_convertidos", 0),
        rating_medio=float(row.get("rating_medio", 0) or 0),
        created_at=str(row["created_at"]),
    )


class ParceiroService:
    def __init__(self, db):
        self.db = db

    async def criar(self, data: ParceiroCreate, curador_id: Optional[UUID] = None) -> ParceiroOut:
        _validar_categorias(data.categorias or [])

        if data.tipo_parceria not in TIPOS_PARCERIA_VALIDOS:
            raise ValueError(f"Tipo de parceria inválido: {data.tipo_parceria}")

        row = await self.db.execute(
            """
            INSERT INTO parceiros (
                nome, descricao, logo_url, site_url, telefone, email,
                categorias, ufs_atuacao, cidades_atuacao, tipo_parceria,
                lead_valor, lead_maximo_mes, comissao_percentual, valor_mensalidade,
                desconto_oferecido, desconto_codigo, diferenciais,
                status, curadoria_por
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, 'PENDENTE', $18)
            RETURNING *
            """,
            data.nome, data.descricao, data.logo_url, data.site_url, data.telefone, data.email,
            data.categorias or [], data.ufs_atuacao or [], data.cidades_atuacao or [], data.tipo_parceria,
            data.lead_valor, data.lead_maximo_mes, data.comissao_percentual, data.valor_mensalidade,
            data.desconto_oferecido, data.desconto_codigo, data.diferenciais or [],
            curador_id
        )
        return _row_to_parceiro_out(row)

    async def listar(
        self,
        status: Optional[str] = None,
        categoria: Optional[str] = None,
        uf: Optional[str] = None,
        tipo_parceria: Optional[str] = None,
        busca: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[list[ParceiroOut], int]:
        where_clauses = ["deleted_at IS NULL"]
        params = []
        param_idx = 1

        if status:
            where_clauses.append(f"status = ${param_idx}")
            params.append(status)
            param_idx += 1

        if categoria:
            where_clauses.append(f"${param_idx} = ANY(categorias)")
            params.append(categoria)
            param_idx += 1

        if uf:
            where_clauses.append(f"${param_idx} = ANY(ufs_atuacao)")
            params.append(uf)
            param_idx += 1

        if tipo_parceria:
            where_clauses.append(f"tipo_parceria = ${param_idx}")
            params.append(tipo_parceria)
            param_idx += 1

        if busca:
            where_clauses.append(f"(nome ILIKE ${param_idx} OR descricao ILIKE ${param_idx})")
            params.append(f"%{busca}%")
            param_idx += 1

        where_sql = " AND ".join(where_clauses)

        count_row = await self.db.fetchrow(
            f"SELECT COUNT(*) FROM parceiros WHERE {where_sql}",
            *params
        )
        total = count_row["count"]

        rows = await self.db.fetch(
            f"""
            SELECT * FROM parceiros
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
            """,
            *params, limit, offset
        )

        return [_row_to_parceiro_out(dict(r)) for r in rows], total

    async def obter(self, parceiro_id: UUID) -> Optional[ParceiroOut]:
        row = await self.db.fetchrow(
            "SELECT * FROM parceiros WHERE id = $1 AND deleted_at IS NULL",
            parceiro_id
        )
        if not row:
            return None
        return _row_to_parceiro_out(dict(row))

    async def atualizar(self, parceiro_id: UUID, data: ParceiroUpdate, curador_id: Optional[UUID] = None) -> Optional[ParceiroOut]:
        updates = []
        params = []
        param_idx = 1

        fields = {
            "nome": data.nome,
            "descricao": data.descricao,
            "logo_url": data.logo_url,
            "site_url": data.site_url,
            "telefone": data.telefone,
            "email": data.email,
            "categorias": data.categorias,
            "ufs_atuacao": data.ufs_atuacao,
            "cidades_atuacao": data.cidades_atuacao,
            "tipo_parceria": data.tipo_parceria,
            "lead_valor": data.lead_valor,
            "lead_maximo_mes": data.lead_maximo_mes,
            "comissao_percentual": data.comissao_percentual,
            "valor_mensalidade": data.valor_mensalidade,
            "desconto_oferecido": data.desconto_oferecido,
            "desconto_codigo": data.desconto_codigo,
            "diferenciais": data.diferenciais,
            "status": data.status,
            "curadoria_nota": data.curadoria_nota,
            "curadoria_observacao": data.curadoria_observacao,
        }

        for field, value in fields.items():
            if value is not None:
                if field == "categorias":
                    _validar_categorias(value)
                updates.append(f"{field} = ${param_idx}")
                params.append(value)
                param_idx += 1

        if curador_id and (data.curadoria_nota is not None or data.curadoria_observacao is not None):
            updates.append(f"curadoria_por = ${param_idx}")
            params.append(curador_id)
            param_idx += 1
            updates.append(f"curadoria_em = NOW()")

        if not updates:
            return await self.obter(parceiro_id)

        params.append(parceiro_id)
        set_sql = ", ".join(updates)

        row = await self.db.fetchrow(
            f"UPDATE parceiros SET {set_sql}, updated_at = NOW() WHERE id = ${param_idx} AND deleted_at IS NULL RETURNING *",
            *params
        )
        if not row:
            return None
        return _row_to_parceiro_out(dict(row))

    async def excluir(self, parceiro_id: UUID) -> bool:
        result = await self.db.execute(
            "UPDATE parceiros SET deleted_at = NOW() WHERE id = $1 AND deleted_at IS NULL",
            parceiro_id
        )
        return result != "UPDATE 0"

    async def buscar_para_tarefa(
        self,
        categoria: str,
        uf: Optional[str] = None,
        cidade: Optional[str] = None,
        limite: int = 3
    ) -> list[ParceiroOut]:
        """
        Retorna parceiros ativos para sugestão em uma tarefa específica.
        Prioriza: sponsored first, depois rating, depois recência.
        """
        where_clauses = [
            "status = 'ATIVO'",
            "deleted_at IS NULL",
            f"'{categoria}' = ANY(categorias)"
        ]
        params = []
        param_idx = 1

        if uf:
            where_clauses.append(f"('{uf}' = ANY(ufs_atuacao) OR ufs_atuacao = '{{}}')")

        if cidade:
            where_clauses.append(f"('{cidade}' = ANY(cidades_atuacao) OR cidades_atuacao = '{{}}')")

        where_sql = " AND ".join(where_clauses)

        rows = await self.db.fetch(
            f"""
            SELECT * FROM parceiros
            WHERE {where_sql}
            ORDER BY
                CASE tipo_parceria WHEN 'SPONSORED' THEN 0 WHEN 'WHITE_LABEL' THEN 1 ELSE 2 END,
                rating_medio DESC,
                created_at DESC
            LIMIT ${param_idx}
            """,
            limite
        )

        return [_row_to_parceiro_out(dict(r)) for r in rows]
