"""Schemas Pydantic do contrato inter-agente (CONSTITUTION C6.2).

LENIENTES por design (`extra="allow"`, campos Optional): o pipeline existente
tolera dicts com múltiplos fallbacks — um schema estrito rejeitaria dado que já
funciona em prod. Aqui o schema DOCUMENTA o contrato e VALIDA os tipos dos campos
conhecidos, sem exigir todos presentes nem proibir extras.

`validar_lenient()` valida + LOGA divergência mas SEMPRE retorna o dado original
(não coage destrutivamente). Assim C6.2 vira contrato verificável e observável,
sem nunca derrubar o pipeline. Endurecer (raise) é um passo futuro, atrás de flag.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger("gymsite.schemas")


class _Lenient(BaseModel):
    model_config = ConfigDict(extra="allow")


class A9Output(_Lenient):
    """Saída do A9 PositioningStrategist (parse do output_key)."""
    veredito_posicionamento: Optional[str] = None
    gaps_identificados: Optional[list] = None
    recomendacao_ticket: Optional[dict] = None
    framework_errc: Optional[dict] = None
    janela_de_entrada: Optional[dict] = None
    markdown: Optional[str] = None
    # PLANO_MOTOR_FINANCEIRO_V3 §2.1/§2.2 — 6 Zonas de Percepção + alertas fiscais/KPI.
    zona_percepcao: Optional[int] = None
    zona_nome: Optional[str] = None
    alertas_financeiros_fiscais: Optional[list] = None


class AnaliseDemografica(_Lenient):
    """Saída do A2 DemoAnalyst (state['analise_demografica'])."""
    codigo_ibge: Optional[Any] = None
    score_demografico: Optional[float] = None
    publico_potencial_fitness: Optional[Any] = None
    insights: Optional[list] = None
    perfil_sexo_publico: Optional[dict] = None
    densidade_setor: Optional[dict] = None


class InteligenciaCompetitiva(_Lenient):
    """Saída do A3b CompetitorAnalysis (output_key='inteligencia_competitiva')."""
    academias_analisadas: Optional[list] = None
    nivel_saturacao: Optional[str] = None
    score_concorrencia: Optional[float] = None
    rating_medio_concorrentes: Optional[float] = None
    total_concorrentes_analisados: Optional[int] = None


class MarketResearch(_Lenient):
    """Saída do A7 MarketResearch (output_key='market_research_result')."""
    # Output é markdown narrativo com seção "## Fontes" obrigatória — validado como str.
    pass


def validar_lenient(modelo: type[BaseModel], dado: Any, *, agente: str) -> Any:
    """Valida `dado` contra `modelo` (leniente) e LOGA divergência. Retorna o `dado`
    original SEMPRE — nunca coage/derruba. C6.2 verificável sem quebrar o tolerante."""
    if not isinstance(dado, dict):
        logger.warning(
            "[schema] %s: output não-dict (%s) — contrato %s espera dict",
            agente, type(dado).__name__, modelo.__name__,
        )
        return dado
    try:
        modelo.model_validate(dado)
    except Exception as e:
        logger.warning(
            "[schema] %s: divergência de contrato (%s): %s",
            agente, modelo.__name__, str(e)[:200],
        )
    return dado
