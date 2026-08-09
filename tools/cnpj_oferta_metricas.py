"""Contagens determinísticas de oferta CNPJ (entrantes / baixas / redes) in-memory."""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any, Callable

from tools.cnpj_oferta_janelas import (
    janela_90d,
    normalize_bairro,
    parse_rfb_date,
    ultimo_trimestre_fechado,
)


def pressao_oferta(saldo: int) -> str:
    if saldo < 0:
        return "retracao"
    if saldo > 0:
        return "expansao"
    return "neutro"


def classificar_raizes_multiunidade(ativos_br: list[dict]) -> set[str]:
    """Raízes com ≥2 estabelecimentos ativos (situacao 02) no conjunto."""
    counts: Counter[str] = Counter()
    for r in ativos_br:
        if not _is_ativo(r.get("situacao_cadastral")):
            continue
        basico = str(r.get("cnpj_basico") or "").strip()
        if not basico and r.get("cnpj"):
            basico = str(r["cnpj"])[:8]
        if basico:
            counts[basico.zfill(8)[:8]] += 1
    return {k for k, n in counts.items() if n >= 2}


def _as_date(v: Any) -> date | None:
    if isinstance(v, date):
        return v
    return parse_rfb_date(v)


def _is_ativo(sit: Any) -> bool:
    return sit in (2, "2", "02") or (str(sit).isdigit() and int(sit) == 2)


def _is_baixada(sit: Any) -> bool:
    return sit in (8, "8", "08") or (str(sit).isdigit() and int(sit) == 8)


def contar_eventos_oferta(
    rows: list[dict],
    *,
    as_of: date,
    bairro_norm: str | None,
    gate_fn: Callable[[dict], bool],
) -> dict[str, Any]:
    """Conta entrantes/baixas em 90d e Q fechado; opcionalmente filtra bairro."""
    q_start, q_end, q_label = ultimo_trimestre_fechado(as_of)
    w90_start, w90_end = janela_90d(as_of)
    bnorm = (bairro_norm or "").strip() or None

    entrantes_90d = entrantes_q = 0
    baixas_90d = baixas_q = 0
    entrantes_b_90d = entrantes_b_q = 0
    baixas_b_90d = baixas_b_q = 0
    estoque = estoque_b = 0

    for r in rows:
        if not gate_fn(r):
            continue
        sit = r.get("situacao_cadastral")
        di = _as_date(r.get("data_inicio_atividade"))
        ds = _as_date(r.get("data_situacao_cadastral"))
        bn = normalize_bairro(str(r.get("bairro") or ""))
        in_bairro = bnorm is not None and bn == bnorm

        if _is_ativo(sit):
            estoque += 1
            if in_bairro:
                estoque_b += 1

        if di is not None:
            if w90_start <= di <= w90_end:
                entrantes_90d += 1
                if in_bairro:
                    entrantes_b_90d += 1
            if q_start <= di <= q_end:
                entrantes_q += 1
                if in_bairro:
                    entrantes_b_q += 1

        if _is_baixada(sit) and ds is not None:
            if w90_start <= ds <= w90_end:
                baixas_90d += 1
                if in_bairro:
                    baixas_b_90d += 1
            if q_start <= ds <= q_end:
                baixas_q += 1
                if in_bairro:
                    baixas_b_q += 1

    saldo_q = entrantes_q - baixas_q
    saldo_b_q = (entrantes_b_q - baixas_b_q) if bnorm else None
    churn_q = round(100.0 * baixas_q / estoque, 2) if estoque else None
    churn_b_q = (
        round(100.0 * baixas_b_q / estoque_b, 2) if bnorm and estoque_b else None
    )

    return {
        "estoque": estoque,
        "estoque_bairro": estoque_b if bnorm else None,
        "entrantes_90d": entrantes_90d,
        "entrantes_q": entrantes_q,
        "baixas_90d": baixas_90d,
        "baixas_q": baixas_q,
        "entrantes_bairro_90d": entrantes_b_90d if bnorm else None,
        "entrantes_bairro_q": entrantes_b_q if bnorm else None,
        "baixas_bairro_90d": baixas_b_90d if bnorm else None,
        "baixas_bairro_q": baixas_b_q if bnorm else None,
        "saldo_oferta_q": saldo_q,
        "saldo_oferta_bairro_q": saldo_b_q,
        "churn_q_pct": churn_q,
        "churn_bairro_q_pct": churn_b_q,
        "pressao_oferta_q": pressao_oferta(saldo_q),
        "janela_q_label": q_label,
        "janela_q_inicio": q_start.isoformat(),
        "janela_q_fim": q_end.isoformat(),
        "janela_90d_inicio": w90_start.isoformat(),
        "janela_90d_fim": w90_end.isoformat(),
        "as_of": as_of.isoformat(),
    }


def bloco_redes(
    rows_ativos_recortados: list[dict],
    raizes_multi: set[str],
    baixas_q_rows: list[dict],
    *,
    bairro_norm: str | None = None,
) -> dict[str, Any]:
    """Conta multiunidade vs solo no recorte; baixas_q split by raiz."""

    def _basico(r: dict) -> str:
        b = str(r.get("cnpj_basico") or "").strip()
        if not b and r.get("cnpj"):
            b = str(r["cnpj"])[:8]
        return b.zfill(8)[:8] if b else ""

    bnorm = (bairro_norm or "").strip() or None
    ativos_multi_mun = ativos_solo_mun = 0
    ativos_multi_b = ativos_solo_b = 0
    for r in rows_ativos_recortados:
        if not _is_ativo(r.get("situacao_cadastral")):
            continue
        multi = _basico(r) in raizes_multi
        if multi:
            ativos_multi_mun += 1
        else:
            ativos_solo_mun += 1
        if bnorm and normalize_bairro(str(r.get("bairro") or "")) == bnorm:
            if multi:
                ativos_multi_b += 1
            else:
                ativos_solo_b += 1

    baixas_multi_q = baixas_solo_q = 0
    for r in baixas_q_rows:
        if not _is_baixada(r.get("situacao_cadastral")):
            continue
        if _basico(r) in raizes_multi:
            baixas_multi_q += 1
        else:
            baixas_solo_q += 1

    com_razao = sum(
        1
        for r in rows_ativos_recortados
        if (r.get("razao_social") or "").strip()
    )
    n_ativos = sum(
        1 for r in rows_ativos_recortados if _is_ativo(r.get("situacao_cadastral"))
    )
    cobertura = round(100.0 * com_razao / n_ativos, 1) if n_ativos else 0.0

    return {
        "ativos_multiunidade_municipio": ativos_multi_mun,
        "ativos_solo_municipio": ativos_solo_mun,
        "ativos_multiunidade_bairro": ativos_multi_b if bnorm else None,
        "ativos_solo_bairro": ativos_solo_b if bnorm else None,
        "baixas_multiunidade_q": baixas_multi_q,
        "baixas_solo_q": baixas_solo_q,
        "criterio": "cnpj_basico com >=2 estab. ativos fitness no BR",
        "razao_social_cobertura_pct": cobertura,
    }
