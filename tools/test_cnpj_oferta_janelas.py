from datetime import date

from tools.cnpj_oferta_janelas import (
    as_of_ref,
    janela_90d,
    normalize_bairro,
    parse_rfb_date,
    ultimo_trimestre_fechado,
)


def test_as_of_atrasado_pelo_ref_month():
    assert as_of_ref(date(2026, 8, 5), date(2026, 5, 1)) == date(2026, 5, 31)


def test_as_of_ref_no_futuro_usa_hoje():
    assert as_of_ref(date(2026, 5, 10), date(2026, 5, 1)) == date(2026, 5, 10)


def test_q_fechado_em_maio_e_q1():
    start, end, label = ultimo_trimestre_fechado(date(2026, 5, 31))
    assert (start, end, label) == (date(2026, 1, 1), date(2026, 3, 31), "2026-Q1")


def test_q_fechado_em_abril_e_q1():
    start, end, label = ultimo_trimestre_fechado(date(2026, 4, 1))
    assert label == "2026-Q1"


def test_janela_90d():
    a, b = janela_90d(date(2026, 5, 31))
    assert b == date(2026, 5, 31)
    assert a == date(2026, 3, 2)  # 31 - 90


def test_parse_rfb_date_int():
    assert parse_rfb_date(20221027) == date(2022, 10, 27)
    assert parse_rfb_date(0) is None
    assert parse_rfb_date(None) is None


def test_normalize_bairro_acento():
    assert normalize_bairro("  Perdízes ") == "PERDIZES"
