"""Reduce market_context / tool payloads for LLM prompts only.

Never mutates the original dict. Downstream agents keep full state data.
Fail-soft: on error, returns the original reference.
"""
from __future__ import annotations

import copy
import logging
from typing import Any

logger = logging.getLogger("gymsite.context_slimmer")

_BLOCOS_REMOVER: list[tuple] = [
    ("cruzamento_cno", "obras_fitness_referencia"),
    ("cruzamento_cno", "benchmark_tempo_obra_cno", "obras_referencia"),
    ("cruzamento_cno", "cno_fitness_keyword_municipio", "obras"),
    ("fatos_parque_cnpj", "cruzamento_cno", "obras_fitness_referencia"),
    ("fatos_parque_cnpj", "cruzamento_cno", "benchmark_tempo_obra_cno", "obras_referencia"),
    ("fatos_parque_cnpj", "cruzamento_cno", "cno_fitness_keyword_municipio", "obras"),
    ("fatos_parque_cnpj", "composicao_parque"),
    ("fatos_parque_cnpj", "metricas"),
    ("fatos_parque_cnpj", "novas_unidades_90d_por_segmento"),
    ("obras_cno_em_curso", "benchmark_tempo_obra"),
    ("zoneamento", "mapa_svg"),
    ("melhores_vias_prospeccao", "mapa_svg"),
]

_CAMPOS_OBRA_REMOVER = {
    "projecao_receita",
    "capacidade_matriculas_estimada",
    "cnaes_obra",
    "previsao_encerramento",
}


def _get_nested(d: dict, path: tuple) -> Any:
    cur = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def _set_nested(d: dict, path: tuple, value: Any) -> None:
    cur = d
    for key in path[:-1]:
        if key not in cur or not isinstance(cur[key], dict):
            return
        cur = cur[key]
    cur[path[-1]] = value


def _resumir_obras_em_curso(obras: list) -> list:
    if not isinstance(obras, list):
        return obras
    resumo = []
    for obra in obras:
        if not isinstance(obra, dict):
            resumo.append(obra)
            continue
        resumo.append({k: v for k, v in obra.items() if k not in _CAMPOS_OBRA_REMOVER})
    return resumo


def _resumir_demanda_futura(demanda: dict) -> dict:
    if not isinstance(demanda, dict):
        return demanda
    slim = copy.deepcopy(demanda)
    for obra in slim.get("obras") or []:
        if isinstance(obra, dict):
            obra.pop("ocupacao_fonte", None)
    return slim


def slim_market_context_for_prompt(market_context: dict) -> dict:
    """Return a prompt-only slim copy. Original dict stays intact."""
    if not isinstance(market_context, dict):
        return market_context

    try:
        slim = copy.deepcopy(market_context)
        stats = {"blocos_removidos": 0, "tokens_estimados_removidos": 0}

        for path in _BLOCOS_REMOVER:
            valor = _get_nested(slim, path)
            if valor is None:
                continue
            tamanho_chars = len(str(valor))
            stats["tokens_estimados_removidos"] += tamanho_chars // 4
            if isinstance(valor, list):
                _set_nested(slim, path, f"[removido: {len(valor)} itens]")
            elif isinstance(valor, dict):
                _set_nested(slim, path, f"[removido: {len(valor)} campos]")
            else:
                _set_nested(slim, path, "[removido]")
            stats["blocos_removidos"] += 1

        obras_bloco = slim.get("obras_cno_em_curso")
        if isinstance(obras_bloco, dict) and obras_bloco.get("obras"):
            obras_bloco["obras"] = _resumir_obras_em_curso(obras_bloco["obras"])

        if isinstance(slim.get("demanda_futura"), dict):
            slim["demanda_futura"] = _resumir_demanda_futura(slim["demanda_futura"])

        fluxo = slim.get("fluxo_pedestre")
        if isinstance(fluxo, dict):
            fluxo.pop("leitura", None)

        # Tool CNPJ: keep scalar metrics, drop heavy nested CNO lists already handled;
        # cap amostra to reduce repeat-tool bloat.
        amostra = slim.get("amostra_entrantes_recentes")
        if isinstance(amostra, list) and len(amostra) > 8:
            slim["amostra_entrantes_recentes"] = amostra[:8]
            slim["amostra_entrantes_recentes_nota"] = (
                f"[amostra truncada para prompt: 8/{len(amostra)}]"
            )

        logger.info(
            "context_slimmer: %d blocos removidos, ~%d tokens reduzidos (prompt only)",
            stats["blocos_removidos"],
            stats["tokens_estimados_removidos"],
        )
        return slim
    except Exception as e:
        logger.warning("context_slimmer falhou, usando original: %s", e)
        return market_context
