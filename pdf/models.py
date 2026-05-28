"""Modelo de view para renderização PDF (independente do JSON canônico A6)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LayoutId(str, Enum):
    """Perfis de modelagem do documento."""

    CLASSIC = "classic"
    """Relatório completo: todas as seções + gráficos (padrão produto)."""
    EXECUTIVE = "executive"
    """Resumo executivo 2–4 páginas: veredito, scores, financeiro mid, top candidatos."""
    DATA_ROOM = "data_room"
    """Ênfase em tabelas e números; menos narrativa (due diligence)."""


@dataclass
class ScoreDim:
    label: str
    value: float | None


@dataclass
class CandidatoPdf:
    posicao: int
    nome: str
    endereco: str
    area_m2: float | None
    score_geoscout: float | None
    score_ancoragem: float | None
    motivo: str


@dataclass
class CenarioPdf:
    modelo: str
    label: str
    ticket_medio: float | None
    receita_mensal: float | None
    lucro_mensal: float | None
    margem_pct: float | None
    payback_meses: int | None
    investimento_total: float | None
    capex_total: float | None
    capex_obra: float | None
    capex_equipamentos: float | None
    capex_contingencia: float | None
    viabilidade: str | None
    matriculas_realista: int | None


@dataclass
class CompetidorPdf:
    nome: str
    rating: float | None
    num_avaliacoes: int | None
    bairro: str | None
    tem_24h: bool | None


@dataclass
class BairroAltPdf:
    bairro: str
    motivo: str
    concorrentes: int | None
    prioridade: str | None


@dataclass
class MarketContextPdf:
    ticket_mercado: str | None
    aluguel_m2: str | None
    renda: str | None
    tendencia: str | None
    redes: list[str] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)
    parque_ativo: int | None = None
    novos_cnpj_90d: int | None = None


@dataclass
class RelatorioPdfModel:
    relatorio_id: str
    data_execucao: str
    cidade: str
    bairro: str
    uf: str | None
    tipo_negocio: str
    area_m2_min: int
    area_m2_max: int
    publico_alvo: str | None

    veredito: str | None
    score_bairro: float | None
    score_top1: float | None
    scores: list[ScoreDim] = field(default_factory=list)
    nivel_saturacao: str | None = None
    total_concorrentes: int | None = None
    total_raio: int | None = None

    resumo_executivo: str | None = None
    posicionamento: str | None = None
    market: MarketContextPdf | None = None

    candidatos: list[CandidatoPdf] = field(default_factory=list)
    cenarios: list[CenarioPdf] = field(default_factory=list)
    modelo_recomendado: str | None = None
    aluguel_mensal: float | None = None
    aluguel_mediana_m2: float | None = None

    competidores: list[CompetidorPdf] = field(default_factory=list)
    bairros_alternativos: list[BairroAltPdf] = field(default_factory=list)
    alertas: list[str] = field(default_factory=list)

    entrantes_cnpj_total: int | None = None
    script_abordagem: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)
