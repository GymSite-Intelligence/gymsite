"""
Matcher — cruza CNPJ fitness entrantes com obras CNO.

Reusa a lógica consagrada de tools.cno_fitness_tools.cruzar_entrantes_obras_cno
e normaliza o resultado em objetos planos para persistência.

Scoring (MODULO_PROSPECCAO §3):
  30% área m² · 25% situação obra · 20% segmento CNPJ · 15% bairro · 10% idade obra
"""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Any

from tools.bairro_normalize import normalizar_bairro
from tools.cno_fitness_tools import _digits, _parse_date_br, cruzar_entrantes_obras_cno
from tools.cnpj_fitness_tools import listar_entrantes_cnpj_fitness

logger = logging.getLogger(__name__)

_FITNESS_SEGMENT_KEYWORDS = (
    "academia", "fitness", "studio", "crossfit", "musculacao", "pilates", "funcional",
)


def match_opportunities(
    *,
    cidade: str,
    uf: str = "CE",
    dias: int = 90,
    limit: int = 500,
    cno_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Executa o cruzamento CNPJ × CNO e retorna uma lista flat de oportunidades
    normalizadas, prontas para enriquecimento e persistência.
    """
    if cno_dir is None:
        from prospecting.config import Config

        cno_dir = Config.resolve_cno_dir()

    # CNO é OPCIONAL. Sem dado CNO, o v2 roda CNPJ-only: cada entrante fitness vira
    # oportunidade (o CNO só reforçaria o score). Mantém o módulo de prospecção
    # independente do CNO e do pipeline de relatório (v1).
    if cno_dir is None:
        return _match_cnpj_only(cidade=cidade, uf=uf, dias=dias, limit=limit)

    raw = cruzar_entrantes_obras_cno(
        cno_dir=cno_dir,
        cidade=cidade,
        uf=uf,
        dias=dias,
        limit=limit,
    )

    if raw.get("status") != "ok":
        # Degrada pra CNPJ-only em vez de derrubar a execução inteira.
        logger.warning(
            "Cruzamento CNO falhou (%s) — caindo pra CNPJ-only em %s/%s",
            raw.get("erro"), cidade, uf,
        )
        return _match_cnpj_only(cidade=cidade, uf=uf, dias=dias, limit=limit)

    oportunidades: list[dict[str, Any]] = []

    for item in raw.get("cruzamentos") or []:
        obra = item.get("obra") or {}
        metodo = item.get("match_cno")
        confianca = item.get("match_confianca")

        # Entrante COM match CNO → score composto; SEM match → score CNPJ-only
        # (não dropa o lead só por ausência de obra).
        if metodo:
            score, motivo = _calcular_score(metodo, confianca, item, obra)
        else:
            score, motivo = _score_cnpj_only(item)

        oportunidades.append(
            _build_opp(item, cidade, uf, obra, score, motivo, metodo, confianca)
        )

    return oportunidades


def _build_opp(
    item: dict,
    cidade: str,
    uf: str,
    obra: dict | None,
    score: float,
    motivo: str,
    metodo: str | None,
    confianca: str | None,
) -> dict[str, Any]:
    """Normaliza um entrante (+ obra CNO opcional) no objeto plano persistível."""
    obra = obra if isinstance(obra, dict) else {}
    return {
        "cnpj": _digits(item.get("cnpj") or ""),
        "razao_social": item.get("razao_social") or item.get("nome_fantasia"),
        "nome_fantasia": item.get("nome_fantasia"),
        "segmento_operacao": item.get("segmento_operacao"),
        "data_inicio_atividade": item.get("data_abertura") or item.get("data_inicio_atividade"),
        "situacao_cadastral": item.get("situacao_cadastral"),
        "cep": _digits(item.get("cep") or ""),
        "endereco_cnpj": {
            "logradouro": item.get("logradouro"),
            "numero": item.get("numero"),
            "bairro": item.get("bairro"),
            "cidade": cidade,
            "uf": uf,
        },
        "cno": obra.get("cno") or None,
        "nome_obra": obra.get("nome_obra") or None,
        "situacao_obra": obra.get("situacao_obra") or None,
        "area_total_m2": obra.get("area_m2") or None,
        "data_inicio_obra": obra.get("data_inicio") or None,
        "data_situacao_obra": obra.get("data_situacao") or None,
        "endereco_cno": {
            "logradouro": obra.get("logradouro") or None,
            "numero": obra.get("numero") or None,
            "bairro": obra.get("bairro") or None,
            "cidade": cidade,
            "uf": uf,
        },
        "score_match": score,
        "motivo_match": motivo,
        "match_metodo": metodo,
        "match_confianca": confianca,
        "projecao_receita": item.get("projecao_receita_estimada"),
        "capacidade_matriculas": item.get("capacidade_matriculas_estimada"),
    }


def _match_cnpj_only(
    *, cidade: str, uf: str, dias: int, limit: int
) -> list[dict[str, Any]]:
    """v2 sem CNO: cada entrante CNPJ fitness do município vira oportunidade.
    Independe de obra CNO e do relatório (v1) — fonte única é o snapshot RFB."""
    res = listar_entrantes_cnpj_fitness(cidade, uf, dias=dias, limit=limit)
    if res.get("status") != "ok":
        logger.warning(
            "listar_entrantes_cnpj_fitness não-ok (%s) p/ %s/%s",
            res.get("status"), cidade, uf,
        )
        return []
    out: list[dict[str, Any]] = []
    for e in res.get("entrantes") or []:
        if not isinstance(e, dict):
            continue
        score, motivo = _score_cnpj_only(e)
        out.append(_build_opp(e, cidade, uf, {}, score, motivo, None, None))
    return out


def _score_area(area_m2: float | None) -> float:
    if not area_m2 or area_m2 <= 0:
        return 0.0
    if area_m2 >= 500:
        return 1.0
    if area_m2 >= 300:
        return 0.75
    if area_m2 >= 150:
        return 0.5
    return 0.25


def _score_situacao_obra(situacao: str | None) -> float:
    s = (situacao or "").lower()
    if "curso" in s or s == "em_curso":
        return 1.0
    if "encerr" in s or "finaliz" in s:
        return 0.55
    return 0.35


def _score_segmento(segmento: str | None) -> float:
    s = (segmento or "").lower()
    if any(k in s for k in _FITNESS_SEGMENT_KEYWORDS):
        return 1.0
    # Entrantes já filtrados como fitness — pontuação base alta
    return 0.85 if segmento else 0.7


def _score_bairro(item: dict, obra: dict | None, metodo: str | None) -> float:
    b_cnpj = normalizar_bairro(item.get("bairro") or "")
    b_obra = normalizar_bairro((obra or {}).get("bairro") or "")
    if b_cnpj and b_obra and b_cnpj == b_obra:
        return 1.0
    cep_cnpj = _digits(item.get("cep"))[:8]
    cep_obra = _digits((obra or {}).get("cep") or "")[:8]
    if cep_cnpj and cep_obra and cep_cnpj == cep_obra:
        return 0.65
    if metodo == "nome_obra_cep8":
        return 0.5
    return 0.0


def _score_idade_obra(data_inicio: str | None) -> float:
    dt = _parse_date_br(data_inicio or "")
    if not dt:
        return 0.4
    months = (date.today() - dt).days / 30.44
    if months <= 6:
        return 1.0
    if months <= 12:
        return 0.7
    if months <= 24:
        return 0.45
    return 0.2


def _calcular_score(
    metodo: str | None,
    confianca: str | None,
    item: dict,
    obra: dict | None,
) -> tuple[float, str]:
    """
    Score composto 0.0–1.0 conforme MODULO_PROSPECCAO §3.
    Sem match CNO válido → 0.0.
    """
    if not metodo:
        return 0.0, "Sem match CNO"

    area = None
    if isinstance(obra, dict):
        try:
            area = float(obra.get("area_m2") or 0) or None
        except (TypeError, ValueError):
            area = None

    s_area = _score_area(area)
    s_sit = _score_situacao_obra((obra or {}).get("situacao_obra") if obra else None)
    s_seg = _score_segmento(item.get("segmento_operacao"))
    s_bairro = _score_bairro(item, obra, metodo)
    s_idade = _score_idade_obra((obra or {}).get("data_inicio") if obra else None)

    weighted = (
        0.30 * s_area
        + 0.25 * s_sit
        + 0.20 * s_seg
        + 0.15 * s_bairro
        + 0.10 * s_idade
    )

    method_floor = {
        "cnpj_responsavel": 0.72,
        "nome_obra_cep8": 0.52,
        "cep8_multiplas_obras": 0.28,
    }.get(metodo, 0.0)

    score = round(min(1.0, max(weighted, method_floor)), 4)

    motivo = (
        f"Match {metodo} ({confianca or '?'}) — "
        f"área={s_area:.0%} situação={s_sit:.0%} segmento={s_seg:.0%} "
        f"bairro={s_bairro:.0%} idade={s_idade:.0%}"
    )
    return score, motivo


def _score_recencia_abertura(data: str | None) -> float:
    """Recência da abertura do CNPJ (ISO ou BR). Mais novo = mais quente."""
    if not data:
        return 0.5
    dt = None
    try:
        dt = date.fromisoformat(data[:10])
    except ValueError:
        dt = _parse_date_br(data)
    if not dt:
        return 0.5
    days = (date.today() - dt).days
    if days <= 30:
        return 1.0
    if days <= 60:
        return 0.8
    if days <= 90:
        return 0.6
    return 0.4


def _score_cnpj_only(item: dict) -> tuple[float, str]:
    """Score sem CNO: segmento (peso maior) + recência da abertura. Piso =
    SCORE_MATCH_MIN pra todo entrante fitness virar lead visível na UI v2 —
    o CNO, quando existe, só reforça o score (não é pré-requisito)."""
    from prospecting.config import Config

    s_seg = _score_segmento(item.get("segmento_operacao"))
    s_rec = _score_recencia_abertura(
        item.get("data_abertura") or item.get("data_inicio_atividade")
    )
    base = 0.6 * s_seg + 0.4 * s_rec
    score = round(min(1.0, max(base, Config.SCORE_MATCH_MIN)), 4)
    return score, f"Entrante CNPJ sem CNO — segmento={s_seg:.0%} recência={s_rec:.0%}"
