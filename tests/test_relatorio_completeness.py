"""Testes da validação de relatório vazio pós-pipeline."""
from tools.relatorio_completeness import (
    EMPTY_REPORT_MSG,
    assess_relatorio_content,
)


def test_empty_when_no_output_and_no_markdown():
    ok, err = assess_relatorio_content(output_row=None, markdown=None)
    assert ok is False
    assert err == EMPTY_REPORT_MSG


def test_ok_with_markdown_only():
    ok, err = assess_relatorio_content(
        output_row=None,
        markdown="# Relatório\n" + ("x" * 250),
    )
    assert ok is True
    assert err == ""


def test_ok_with_scores_partial_no_candidatos():
    ok, err = assess_relatorio_content(
        output_row={
            "veredito": "APROVADO",
            "score_bairro": 8.0,
            "score_demografico": 7.5,
        },
        candidatos_count=0,
        competidores_count=0,
    )
    assert ok is True


def test_empty_output_row_only_default_veredito():
    ok, err = assess_relatorio_content(
        output_row={"veredito": "REPROVADO"},
    )
    assert ok is False


def test_ok_with_cenarios_children():
    ok, err = assess_relatorio_content(
        output_row={"veredito": "REPROVADO"},
        cenarios_count=3,
    )
    assert ok is True
