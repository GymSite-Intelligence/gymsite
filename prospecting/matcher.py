"""
Matcher — cruza CNPJ fitness entrantes com obras CNO.

Reusa a lógica consagrada de tools.cno_fitness_tools.cruzar_entrantes_obras_cno
e normaliza o resultado em objetos planos para persistência.

Scoring (MODULO_PROSPECCAO §3):
  30% área m² · 25% situação obra · 20% segmento CNPJ · 15% bairro · 10% idade obra
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from tools.bairro_normalize import normalizar_bairro
from tools.cno_fitness_tools import _digits, _parse_date_br, cruzar_entrantes_obras_cno

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

    if cno_dir is None:
        raise RuntimeError(
            "CNO_DATA_DIR não configurado. "
            "Defina a variável de ambiente CNO_DATA_DIR."
        )

    raw = cruzar_entrantes_obras_cno(
        cno_dir=cno_dir,
        cidade=cidade,
        uf=uf,
        dias=dias,
        limit=limit,
    )

    if raw.get("status") != "ok":
        raise RuntimeError(f"Falha no cruzamento: {raw.get('erro') or raw}")

    oportunidades: list[dict[str, Any]] = []

    for item in raw.get("cruzamentos") or []:
        obra = item.get("obra") or {}
        metodo = item.get("match_cno")
        confianca = item.get("match_confianca")

        score, motivo = _calcular_score(metodo, confianca, item, obra)

        opp: dict[str, Any] = {
            "cnpj": _digits(item.get("cnpj")),
            "razao_social": item.get("razao_social") or item.get("nome_fantasia"),
            "nome_fantasia": item.get("nome_fantasia"),
            "segmento_operacao": item.get("segmento_operacao"),
            "data_inicio_atividade": item.get("data_abertura"),
            "situacao_cadastral": item.get("situacao_cadastral"),
            "cep": _digits(item.get("cep")),
            "endereco_cnpj": {
                "logradouro": item.get("logradouro"),
                "numero": item.get("numero"),
                "bairro": item.get("bairro"),
                "cidade": cidade,
                "uf": uf,
            },
            "cno": obra.get("cno") if isinstance(obra, dict) else None,
            "nome_obra": obra.get("nome_obra") if isinstance(obra, dict) else None,
            "situacao_obra": obra.get("situacao_obra") if isinstance(obra, dict) else None,
            "area_total_m2": obra.get("area_m2") if isinstance(obra, dict) else None,
            "data_inicio_obra": obra.get("data_inicio") if isinstance(obra, dict) else None,
            "data_situacao_obra": obra.get("data_situacao") if isinstance(obra, dict) else None,
            "endereco_cno": {
                "logradouro": obra.get("logradouro") if isinstance(obra, dict) else None,
                "numero": obra.get("numero") if isinstance(obra, dict) else None,
                "bairro": obra.get("bairro") if isinstance(obra, dict) else None,
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
        oportunidades.append(opp)

    return oportunidades


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
