"""Re-export estável — L1 dados, L2 RAG, Eros (compat ADK imports)."""
from __future__ import annotations

from agents_site.tools_eros import (
    consultar_eros_arquiteto,
    consultar_eros_engenharia,
    consultar_eros_mercado,
    consultar_eros_regulatorio,
    consultar_eros_tecnico,
    criar_tool_consultar_eros,
)
from agents_site.tools_l1_dados import (
    analisar_demografia,
    analisar_reviews_e_dores,
    buscar_concorrentes,
    buscar_pontos_comerciais,
    calcular_equipamentos_por_area,
    calcular_sanitarios_por_lotacao,
    dimensionar_cardio_por_pico,
    dimensionar_musculacao,
    estimar_investimento,
    gerar_planta_layout_zonas,
    pesquisar_contexto_mercado,
)
from agents_site.tools_l2_rag import (
    _pack_eros_as_resultados,
    _rag_cascade,
    consultar_base_mercado,
    consultar_base_regulatoria,
    consultar_catalogo_equipamentos,
    consultar_engenharia_obra,
)

__all__ = [
    "analisar_demografia",
    "analisar_reviews_e_dores",
    "buscar_concorrentes",
    "buscar_pontos_comerciais",
    "calcular_equipamentos_por_area",
    "calcular_sanitarios_por_lotacao",
    "consultar_base_mercado",
    "consultar_base_regulatoria",
    "consultar_catalogo_equipamentos",
    "consultar_engenharia_obra",
    "consultar_eros_arquiteto",
    "consultar_eros_engenharia",
    "consultar_eros_mercado",
    "consultar_eros_regulatorio",
    "consultar_eros_tecnico",
    "criar_tool_consultar_eros",
    "dimensionar_cardio_por_pico",
    "dimensionar_musculacao",
    "estimar_investimento",
    "gerar_planta_layout_zonas",
    "pesquisar_contexto_mercado",
    "_pack_eros_as_resultados",
    "_rag_cascade",
]
