"""Sanitizador de tipos para gravação no Supabase (PONTO 75 — bug \"5.0\" em integer).

Coerção defensiva: não inventa valor, preserva None, fail-soft.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("gymsite.supabase_sanitizer")

# Campos integer / smallint no schema das tabelas do writer.
_INT_FIELDS = frozenset({
    "area_m2",
    "area_estimada_m2",
    "area_m2_min",
    "area_m2_max",
    "num_avaliacoes",
    "populacao",
    "domicilios",
    "gated_n",
    "n_poligono",
    "total_concorrentes_analisados",
    "total_encontrados_raio",
    "ranking_cidade",
    "n_setores",
    "total_obras_em_curso",
    "n_obras",
    "provavel_residencial_n",
    "claims_verificadas",
    "claims_com_alertas",
    "total_processados",
    "sucessos",
    "queries_aluguel_com_dados",
    "posicao",
    "ordem",
    "concorrentes_no_bairro",
    "matriculas_conservador",
    "matriculas_realista",
    "matriculas_agressivo",
    "capacidade_simultanea_pico",
    "alunos_pico_calculado",
    "capacidade_maxima_alunos",
    "alunos_projetados",
    "alunos_break_even",
    "payback_meses",
    "capital_giro_meses",
    "tempo_execucao_segundos",
    "situacao_cadastral",
})

_FLOAT_FIELDS = frozenset({
    "score_bairro",
    "score_top1_candidato",
    "score_demografico",
    "score_concorrencia",
    "score_viabilidade",
    "score_geoscout",
    "score_ancoragem",
    "score_geral",
    "score_validacao",
    "renda_media",
    "renda_pc",
    "renda_resp_domicilio",
    "renda_percentil",
    "renda_media_bairro",
    "fluxo_score",
    "fluxo_norm",
    "mean_flow_score",
    "aluguel_mensal",
    "aluguel_min_m2",
    "aluguel_max_m2",
    "aluguel_mediana_m2",
    "aluguel_unitario_m2",
    "aluguel_estimado",
    "aluguel_mrlr_mensal",
    "n_per_10k",
    "ticket_recomendado",
    "ticket_mercado",
    "ticket_medio",
    "ticket_teto_sustentavel",
    "ticket_piso_ocupacao",
    "ticket_realizado_estimado",
    "rating",
    "rating_geral",
    "rating_oficial",
    "rating_medio_concorrentes",
    "percentil",
    "media_moradores",
    "margem_percentual",
    "densidade_por_km2",
    "raio_km",
    "distancia_km",
    "taxa_sucesso",
    "preco_mensal_brl",
    "lat",
    "lng",
    "matr_por_m2_realista",
    "frequencia_semanal_aluno",
    "pico_share",
    "folga_capacidade_pct",
    "taxa_inadimplencia",
    "taxa_cancelamento_mensal",
    "receita_mensal",
    "custo_aluguel",
    "custo_condominio",
    "custo_iptu",
    "custo_energia",
    "custo_agua",
    "custo_internet",
    "custo_folha",
    "custo_manutencao",
    "custo_contabilidade",
    "custo_sistema_gestao",
    "custo_seguro",
    "custo_outros",
    "custos_fixos_total",
    "custos_fixos",
    "marketing_pct_faturamento",
    "marketing_mensal",
    "custos_totais",
    "lucro_mensal_estimado",
    "lucro_mensal",
    "capex_equipamentos",
    "capex_obra_adaptacao",
    "capex_projeto_arquitetonico",
    "capex_alvara_e_taxas",
    "capex_contingencia_pct",
    "capex_contingencia_valor",
    "capex_total",
    "capex_estimado",
    "fator_r",
    "aliquota_tributos",
    "tributos_mensal",
    "capital_giro",
    "investimento_total",
    "tir_anual_pct",
    "vpl_5_anos",
})


def _coerce_int(val: Any) -> int | None:
    if val is None:
        return None
    if isinstance(val, bool):
        return int(val)
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        if val == int(val):
            return int(val)
        logger.warning(
            "supabase_sanitizer: float fracionário %r não convertido para int",
            val,
        )
        return None
    if isinstance(val, str):
        try:
            f = float(val.strip())
            if f == int(f):
                return int(f)
            return None
        except (ValueError, TypeError):
            logger.warning(
                "supabase_sanitizer: string %r não parseável como int",
                val,
            )
            return None
    logger.warning(
        "supabase_sanitizer: tipo inesperado %s para int",
        type(val).__name__,
    )
    return None


def _coerce_float(val: Any) -> float | None:
    if val is None:
        return None
    if isinstance(val, bool):
        return float(val)
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val.strip())
        except (ValueError, TypeError):
            logger.warning(
                "supabase_sanitizer: string %r não parseável como float",
                val,
            )
            return None
    logger.warning(
        "supabase_sanitizer: tipo inesperado %s para float",
        type(val).__name__,
    )
    return None


def sanitize_record(record: dict) -> tuple[dict, dict]:
    """Coerce tipos conhecidos. Retorna (record_limpo, stats)."""
    if not isinstance(record, dict):
        return record, {"erro": "record não é dict"}

    limpo: dict = {}
    stats = {"int_convertidos": 0, "float_convertidos": 0, "nullificados": 0}

    for key, val in record.items():
        original = val

        if key in _INT_FIELDS:
            convertido = _coerce_int(val)
            limpo[key] = convertido
            already_int = isinstance(original, int) and not isinstance(original, bool)
            if convertido is not None and not already_int:
                stats["int_convertidos"] += 1
            elif convertido is None and original is not None:
                stats["nullificados"] += 1
        elif key in _FLOAT_FIELDS:
            convertido = _coerce_float(val)
            limpo[key] = convertido
            already_float = isinstance(original, float)
            if convertido is not None and not already_float:
                stats["float_convertidos"] += 1
            elif convertido is None and original is not None:
                stats["nullificados"] += 1
        else:
            limpo[key] = val

    if stats["int_convertidos"] or stats["float_convertidos"] or stats["nullificados"]:
        logger.info(
            "supabase_sanitizer: %d int convertidos, %d float convertidos, %d nullificados",
            stats["int_convertidos"],
            stats["float_convertidos"],
            stats["nullificados"],
        )

    return limpo, stats


def sanitize_nested_records(data: Any, depth: int = 0, max_depth: int = 3) -> Any:
    """Sanitiza dicts/listas aninhados (ex.: top_3_candidatos)."""
    if depth > max_depth:
        return data

    if isinstance(data, dict):
        has_mapped = any(k in _INT_FIELDS or k in _FLOAT_FIELDS for k in data.keys())
        sanitizado = sanitize_record(data)[0] if has_mapped else data
        resultado = {}
        for key, val in sanitizado.items():
            if isinstance(val, (dict, list)):
                resultado[key] = sanitize_nested_records(val, depth + 1, max_depth)
            else:
                resultado[key] = val
        return resultado

    if isinstance(data, list):
        return [sanitize_nested_records(item, depth + 1, max_depth) for item in data]

    return data
