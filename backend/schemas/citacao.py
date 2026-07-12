"""
backend/schemas/citacao.py
===========================
Pydantic schema for structured citations (Carimbo da Fonte).
"""
from typing import Optional
from pydantic import BaseModel, Field

class Citation(BaseModel):
    """
    Representa uma citação estruturada de uma fonte de dados, espelhando
    o componente `CitationStamp.tsx` do frontend.
    """
    valor: Optional[str] = Field(default=None, description="O valor ou dado específico sendo citado. Ex: '1.200kg/m²'")
    base: Optional[str] = Field(default=None, description="A base ou contexto da informação. Ex: 'Carga Estrutural'")
    fonte: Optional[str] = Field(default=None, description="A fonte da informação. Ex: 'ABNT NBR 6120'")
    janela: Optional[str] = Field(default=None, description="A janela de tempo da validade do dado. Ex: '2019'")
    url: Optional[str] = Field(default=None, description="URL verificável para a fonte, se disponível.")

