# models/schemas.py
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class SearchRequest:
    cidade: str
    estado: str
    bairros: list[str] = field(default_factory=list)
    area_minima_m2: int = 1000
    area_maxima_m2: int = 1500
    raio_busca_km: float = 5.0
    exigir_terreo: bool = True
    exigir_estacionamento: bool = True
    publico_alvo_faixa_etaria: str = "18-45"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Coordenada:
    latitude: float
    longitude: float


@dataclass
class PontoComercial:
    place_id: str
    nome: str
    endereco: str
    coordenada: Coordenada
    area_estimada_m2: Optional[float] = None
    terreo: bool = False
    tem_estacionamento: bool = False
    score_geoscout: float = 0.0
    foto_url: Optional[str] = None
    street_view_url: Optional[str] = None
    tipos: list[str] = field(default_factory=list)
    status: Optional[str] = None


@dataclass
class AnalyseDemografica:
    municipio: str
    codigo_ibge: str
    populacao_total: int
    populacao_faixa_alvo: int
    percentual_faixa_alvo: float
    renda_media_domiciliar: Optional[float] = None
    score_demografico: float = 0.0
    insights: list[str] = field(default_factory=list)


@dataclass
class Concorrente:
    nome: str
    endereco: str
    distancia_km: float
    rating: Optional[float] = None
    num_avaliacoes: int = 0
    nivel_preco: Optional[str] = None


@dataclass
class AnalyseConcorrencia:
    total_concorrentes: int
    concorrentes: list[Concorrente] = field(default_factory=list)
    nivel_saturacao: str = "BAIXO"
    oportunidades: list[str] = field(default_factory=list)
    score_concorrencia: float = 0.0


@dataclass
class EstimativaFinanceira:
    aluguel_estimado_mensal: float
    aluguel_min: float
    aluguel_max: float
    investimento_total_estimado: float
    ticket_medio_mensalidade: float
    alunos_necessarios_break_even: int
    payback_estimado_meses: int
    score_viabilidade: float = 0.0
    alertas: list[str] = field(default_factory=list)


@dataclass
class Contato:
    tipo: str
    nome: Optional[str] = None
    empresa: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    script_abordagem: Optional[str] = None
    canal_recomendado: str = "WHATSAPP"


@dataclass
class ListingResult:
    """Anúncio de imóvel comercial extraído de portal externo (OLX/ImovelWeb).
    Consumido por A1 GeoScout pra cruzar com zonas Places. Ver docs/listing_sources.md."""
    source: str                          # "olx" | "imovelweb"
    title: str
    price_raw: str                       # "R$ 28.000/mês" — A4 parseia depois
    area_m2: int
    address: str
    listing_url: str                     # URL clicável do anúncio
    source_url: str                      # URL da página de listagem usada
    listing_id: str = ""                 # ID numérico final do URL (chave de dedup)
    description: str = ""
    price_numeric: Optional[float] = None
    property_type: str = "comercial"     # "loja" | "galpao" | "predio" (LLM infere)
    parking: Optional[bool] = None
    floor_type: Optional[str] = None     # "terreo" | "andar"
    tipo_imovel_codigo_onr: Optional[int] = None
    tipo_imovel_label: Optional[str] = None
    modalidade: Optional[str] = None

