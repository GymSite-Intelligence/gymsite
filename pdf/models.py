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
    BALA = "bala"
    """Layout premium: capa impactante, cards de KPI, hierarquia visual moderna."""


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
    tipo_imovel_codigo_onr: int | None = None
    tipo_imovel_label: str | None = None
    modalidade: str | None = None
    cartorio: dict | None = None
    # R1 — Street View (evidencia visual do endereco-ancora); opcionais, default None
    lat: float | None = None
    lng: float | None = None
    street_view_url: str | None = None
    street_view_path: str | None = None


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
    capex_frete: float | None = None
    capital_giro: float | None = None
    taxa_inadimplencia: float | None = None
    ticket_realizado: float | None = None
    # V3 (A4) — tributos & ocupação por cenário; opcionais (relatórios antigos não têm).
    tributos_mensal: float | None = None
    aliquota_tributos: float | None = None  # fração (ex 0.06)
    anexo_simples: str | None = None  # "III" | "V"
    fator_r: float | None = None  # fração (ex 0.35)
    folha_pct_efetivo: float | None = None  # fração
    ocupacao_pct: float | None = None  # fração (ex 0.4035)
    teto_ocupacao: float | None = None  # fração (ex 0.15)
    ticket_piso_ocupacao: float | None = None  # R$
    ocupacao_estoura: bool | None = None
    justificativa: str | None = None  # motivo do selo de viabilidade (A4 _classificar_viabilidade)


@dataclass
class CompetidorPdf:
    nome: str
    rating: float | None
    num_avaliacoes: int | None
    bairro: str | None
    tem_24h: bool | None
    planos_precos: list | None = None
    # Camada 3 — agregadores (tier corporativo ≠ preço de balcão; rating com fonte).
    tier_agregador: dict | None = None
    rating_agregador: dict | None = None
    oferta_modalidades: list | None = None   # chaves canônicas do catálogo (minerado)
    oferta_comodidades: list | None = None   # texto livre do Wellhub
    oferta_fontes: list | None = None        # ["website", "instagram", "wellhub"]
    # B3 — gated da praça: analisado (deep) | mapeado (só gate)
    profundidade: str | None = None
    place_id: str | None = None
    endereco: str | None = None


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
    # Oferta CNPJ — baixas first-class (spec 2026-08-05)
    baixas_cnpj_90d: int | None = None
    baixas_cnpj_q: int | None = None
    entrantes_cnpj_q: int | None = None
    saldo_oferta_q: int | None = None
    pressao_oferta_q: str | None = None
    janela_q_label: str | None = None
    cnpj_as_of: str | None = None
    baixas_bairro_90d: int | None = None
    baixas_bairro_q: int | None = None
    entrantes_bairro_q: int | None = None
    saldo_bairro_q: int | None = None
    ref_month_cnpj: str | None = None


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
    posicionamento_estrategico: dict | None = None
    market: MarketContextPdf | None = None

    candidatos: list[CandidatoPdf] = field(default_factory=list)
    cenarios: list[CenarioPdf] = field(default_factory=list)
    modelo_recomendado: str | None = None
    aluguel_mensal: float | None = None
    aluguel_mediana_m2: float | None = None
    aluguel_fonte: str | None = None

    competidores: list[CompetidorPdf] = field(default_factory=list)
    bairros_alternativos: list[BairroAltPdf] = field(default_factory=list)
    alertas: list[str] = field(default_factory=list)

    entrantes_cnpj_total: int | None = None
    entrantes_cnpj_bairro: int | None = None
    entrantes_cnpj_bairro_nome: str | None = None
    script_abordagem: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)
