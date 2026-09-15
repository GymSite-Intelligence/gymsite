# models/schemas.py
from dataclasses import dataclass
from typing import Optional


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
