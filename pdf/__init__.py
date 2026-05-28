"""
GymSite Intelligence — geração de PDF de relatório (produto).

Uso rápido:
    from pdf import generate_relatorio_pdf, LayoutId
    from pdf.adapters import relatorio_from_api_payload

    model = relatorio_from_api_payload(api.get_relatorio(id))
    pdf_bytes = generate_relatorio_pdf(model, layout=LayoutId.CLASSIC)
"""

from pdf.builder import generate_relatorio_pdf
from pdf.models import LayoutId, RelatorioPdfModel

__all__ = [
    "LayoutId",
    "RelatorioPdfModel",
    "generate_relatorio_pdf",
]
