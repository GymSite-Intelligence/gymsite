"""
Validação de conteúdo mínimo após o pipeline (relatório não pode ficar vazio com status done).
"""
from __future__ import annotations

from typing import Any, Optional

EMPTY_REPORT_MSG = (
    "Relatório vazio: pipeline concluiu sem conteúdo. "
    "Use «Gerar novamente» para reprocessar."
)

# Texto curto demais não conta como relatório utilizável no viewer.
_MIN_RESUMO_LEN = 40
_MIN_MARKDOWN_LEN = 200


def _nonempty_str(value: Any, *, min_len: int) -> bool:
    if not isinstance(value, str):
        return False
    return len(value.strip()) >= min_len


def _has_numeric_score(output_row: dict) -> bool:
    for key in (
        "score_bairro",
        "score_top1_candidato",
        "score_demografico",
        "score_concorrencia",
        "score_viabilidade",
    ):
        val = output_row.get(key)
        if isinstance(val, (int, float)) and val > 0:
            return True
    return False


def assess_relatorio_content(
    *,
    output_row: Optional[dict[str, Any]],
    markdown: Optional[str] = None,
    candidatos_count: int = 0,
    competidores_count: int = 0,
    cenarios_count: int = 0,
    bairros_alt_count: int = 0,
) -> tuple[bool, str]:
    """
    Retorna (ok, erro). ok=True quando há conteúdo suficiente para o viewer.

    Relatórios parciais (scores + cenários financeiros, sem candidatos) são aceitos.
    Falha quando não há linha em relatorio_outputs e nem markdown substantivo.
    """
    has_markdown = _nonempty_str(markdown, min_len=_MIN_MARKDOWN_LEN)
    has_children = (
        candidatos_count > 0
        or competidores_count > 0
        or cenarios_count > 0
        or bairros_alt_count > 0
    )

    if output_row is None:
        if has_markdown or has_children:
            return True, ""
        return False, EMPTY_REPORT_MSG

    has_resumo = _nonempty_str(output_row.get("resumo_executivo"), min_len=_MIN_RESUMO_LEN)
    has_score = _has_numeric_score(output_row)
    veredito = (output_row.get("veredito") or "").strip()

    if has_markdown or has_children or has_resumo or has_score:
        return True, ""

    # Veredito explícito sem scores nem filhos — ainda é conteúdo mínimo narrativo.
    if veredito and veredito not in ("", "REPROVADO"):
        return True, ""

    return False, EMPTY_REPORT_MSG


def fetch_relatorio_content_snapshot(sb: Any, relatorio_id: str) -> dict[str, Any]:
    """Lê header + outputs + contagens filhas para validação."""
    header = (
        sb.table("relatorios")
        .select("markdown_completo")
        .eq("id", relatorio_id)
        .maybe_single()
        .execute()
    )
    outputs = (
        sb.table("relatorio_outputs")
        .select("*")
        .eq("relatorio_id", relatorio_id)
        .maybe_single()
        .execute()
    )

    def _count(table: str) -> int:
        res = (
            sb.table(table)
            .select("id", count="exact")
            .eq("relatorio_id", relatorio_id)
            .limit(1)
            .execute()
        )
        return int(res.count or 0)

    header_data = header.data if header else None
    return {
        "markdown": (header_data or {}).get("markdown_completo"),
        "output_row": outputs.data if outputs else None,
        "candidatos_count": _count("candidatos"),
        "competidores_count": _count("competidores"),
        "cenarios_count": _count("cenarios_financeiros"),
        "bairros_alt_count": _count("bairros_alternativos"),
    }


def validate_relatorio_has_content(sb: Any, relatorio_id: str) -> tuple[bool, str]:
    snap = fetch_relatorio_content_snapshot(sb, relatorio_id)
    return assess_relatorio_content(
        output_row=snap.get("output_row"),
        markdown=snap.get("markdown"),
        candidatos_count=int(snap.get("candidatos_count") or 0),
        competidores_count=int(snap.get("competidores_count") or 0),
        cenarios_count=int(snap.get("cenarios_count") or 0),
        bairros_alt_count=int(snap.get("bairros_alt_count") or 0),
    )
