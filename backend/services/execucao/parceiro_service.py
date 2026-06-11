"""
Parceiro Service — CRUD de fornecedores curados para o playbook.

Acesso admin para cadastro, curadoria e gestão de parceiros.
Usa supabase-py (padrão do projeto). Valores monetários em centavos (int).
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID


@dataclass
class ParceiroCreate:
    nome: str
    descricao: Optional[str] = None
    logo_url: Optional[str] = None
    site_url: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    categorias: Optional[list[str]] = None
    ufs_atuacao: Optional[list[str]] = None
    cidades_atuacao: Optional[list[str]] = None
    tipo_parceria: str = "LEAD_GENERATION"
    lead_valor: Optional[int] = None
    lead_maximo_mes: Optional[int] = None
    comissao_percentual: Optional[float] = None
    valor_mensalidade: Optional[int] = None
    desconto_oferecido: Optional[str] = None
    desconto_codigo: Optional[str] = None
    diferenciais: Optional[list[str]] = None


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
    lead_valor: Optional[int] = None
    lead_maximo_mes: Optional[int] = None
    comissao_percentual: Optional[float] = None
    valor_mensalidade: Optional[int] = None
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
    lead_valor: Optional[int]
    lead_maximo_mes: Optional[int]
    comissao_percentual: Optional[float]
    valor_mensalidade: Optional[int]
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


CATEGORIAS_VALIDAS = {
    "IMOBILIARIO", "LEGAL", "OBRAS", "EQUIPAMENTOS",
    "TECNOLOGIA", "RH", "MARKETING", "FINANCEIRO", "OPERACIONAL", "OUTRO"
}

TIPOS_PARCERIA_VALIDOS = {"LEAD_GENERATION", "AFILIADO", "SPONSORED", "WHITE_LABEL"}
STATUS_VALIDOS = {"PENDENTE", "ATIVO", "PAUSADO", "CANCELADO", "REPROVADO"}

_CAMPOS_UPDATE = (
    "nome", "descricao", "logo_url", "site_url", "telefone", "email",
    "categorias", "ufs_atuacao", "cidades_atuacao", "tipo_parceria",
    "lead_valor", "lead_maximo_mes", "comissao_percentual", "valor_mensalidade",
    "desconto_oferecido", "desconto_codigo", "diferenciais",
    "status", "curadoria_nota", "curadoria_observacao",
)


def _validar_categorias(categorias: list[str]) -> None:
    invalidas = set(categorias or []) - CATEGORIAS_VALIDAS
    if invalidas:
        raise ValueError(f"Categorias inválidas: {invalidas}")


def _row_to_parceiro_out(row: dict[str, Any]) -> ParceiroOut:
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
        lead_valor=int(row["lead_valor"]) if row.get("lead_valor") is not None else None,
        lead_maximo_mes=row.get("lead_maximo_mes"),
        comissao_percentual=float(row["comissao_percentual"]) if row.get("comissao_percentual") is not None else None,
        valor_mensalidade=int(row["valor_mensalidade"]) if row.get("valor_mensalidade") is not None else None,
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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ParceiroService:
    """CRUD sobre a tabela parceiros via supabase-py (service role)."""

    def __init__(self, sb):
        self.sb = sb

    def criar(self, data: ParceiroCreate, curador_id: Optional[str] = None) -> ParceiroOut:
        _validar_categorias(data.categorias or [])
        if data.tipo_parceria not in TIPOS_PARCERIA_VALIDOS:
            raise ValueError(f"Tipo de parceria inválido: {data.tipo_parceria}")

        payload = {
            "nome": data.nome,
            "descricao": data.descricao,
            "logo_url": data.logo_url,
            "site_url": data.site_url,
            "telefone": data.telefone,
            "email": data.email,
            "categorias": data.categorias or [],
            "ufs_atuacao": data.ufs_atuacao or [],
            "cidades_atuacao": data.cidades_atuacao or [],
            "tipo_parceria": data.tipo_parceria,
            "lead_valor": data.lead_valor,
            "lead_maximo_mes": data.lead_maximo_mes,
            "comissao_percentual": data.comissao_percentual,
            "valor_mensalidade": data.valor_mensalidade,
            "desconto_oferecido": data.desconto_oferecido,
            "desconto_codigo": data.desconto_codigo,
            "diferenciais": data.diferenciais or [],
            "status": "PENDENTE",
            "curadoria_por": curador_id,
        }
        res = self.sb.table("parceiros").insert(payload).execute()
        return _row_to_parceiro_out(res.data[0])

    def listar(
        self,
        status: Optional[str] = None,
        categoria: Optional[str] = None,
        uf: Optional[str] = None,
        tipo_parceria: Optional[str] = None,
        busca: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ParceiroOut], int]:
        query = (
            self.sb.table("parceiros")
            .select("*", count="exact")
            .is_("deleted_at", "null")
        )
        if status:
            query = query.eq("status", status)
        if categoria:
            query = query.contains("categorias", [categoria])
        if uf:
            query = query.contains("ufs_atuacao", [uf])
        if tipo_parceria:
            query = query.eq("tipo_parceria", tipo_parceria)
        if busca:
            query = query.or_(f"nome.ilike.%{busca}%,descricao.ilike.%{busca}%")

        res = (
            query.order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        items = [_row_to_parceiro_out(r) for r in (res.data or [])]
        return items, res.count or 0

    def obter(self, parceiro_id: UUID) -> Optional[ParceiroOut]:
        res = (
            self.sb.table("parceiros")
            .select("*")
            .eq("id", str(parceiro_id))
            .is_("deleted_at", "null")
            .maybe_single()
            .execute()
        )
        if not res or not res.data:
            return None
        return _row_to_parceiro_out(res.data)

    def atualizar(
        self,
        parceiro_id: UUID,
        data: ParceiroUpdate,
        curador_id: Optional[str] = None,
    ) -> Optional[ParceiroOut]:
        updates: dict[str, Any] = {}
        for campo in _CAMPOS_UPDATE:
            valor = getattr(data, campo)
            if valor is not None:
                if campo == "categorias":
                    _validar_categorias(valor)
                if campo == "tipo_parceria" and valor not in TIPOS_PARCERIA_VALIDOS:
                    raise ValueError(f"Tipo de parceria inválido: {valor}")
                if campo == "status" and valor not in STATUS_VALIDOS:
                    raise ValueError(f"Status inválido: {valor}")
                updates[campo] = valor

        if not updates:
            return self.obter(parceiro_id)

        if curador_id and (data.curadoria_nota is not None or data.curadoria_observacao is not None):
            updates["curadoria_por"] = curador_id
            updates["curadoria_em"] = _now_iso()

        updates["updated_at"] = _now_iso()

        res = (
            self.sb.table("parceiros")
            .update(updates)
            .eq("id", str(parceiro_id))
            .is_("deleted_at", "null")
            .execute()
        )
        if not res.data:
            return None
        return _row_to_parceiro_out(res.data[0])

    def excluir(self, parceiro_id: UUID) -> bool:
        res = (
            self.sb.table("parceiros")
            .update({"deleted_at": _now_iso()})
            .eq("id", str(parceiro_id))
            .is_("deleted_at", "null")
            .execute()
        )
        return bool(res.data)

    def buscar_para_tarefa(
        self,
        categoria: str,
        uf: Optional[str] = None,
        cidade: Optional[str] = None,
        limite: int = 3,
    ) -> list[ParceiroOut]:
        """Parceiros ativos para sugestão em uma tarefa do playbook.
        Prioriza sponsored, depois rating, depois recência. Filtro de
        uf/cidade aceita parceiro de cobertura nacional (arrays vazios)."""
        res = (
            self.sb.table("parceiros")
            .select("*")
            .eq("status", "ATIVO")
            .is_("deleted_at", "null")
            .contains("categorias", [categoria])
            .execute()
        )
        candidatos = [_row_to_parceiro_out(r) for r in (res.data or [])]

        if uf:
            candidatos = [p for p in candidatos if not p.ufs_atuacao or uf in p.ufs_atuacao]
        if cidade:
            candidatos = [p for p in candidatos if not p.cidades_atuacao or cidade in p.cidades_atuacao]

        ordem_tipo = {"SPONSORED": 0, "WHITE_LABEL": 1}
        candidatos.sort(
            key=lambda p: (
                ordem_tipo.get(p.tipo_parceria, 2),
                -p.rating_medio,
                p.created_at,
            )
        )
        return candidatos[:limite]
