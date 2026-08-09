from datetime import date

from tools.cnpj_oferta_metricas import (
    classificar_raizes_multiunidade,
    contar_eventos_oferta,
    pressao_oferta,
)


def _row(**kw):
    base = {
        "situacao_cadastral": 2,
        "bairro": "PERDIZES",
        "cnpj": "1",
        "cnpj_basico": "11111111",
        "nome_fantasia": "GYM X",
        "cnae_fiscal_principal": "9313100",
        "cnaes_secundarios": "",
        "data_inicio_atividade": date(2020, 1, 1),
        "data_situacao_cadastral": date(2020, 1, 1),
    }
    base.update(kw)
    return base


def test_baixas_e_entrantes_q_e_90d():
    as_of = date(2026, 5, 31)
    rows = [
        _row(cnpj="a", data_inicio_atividade=date(2026, 4, 1), situacao_cadastral=2),
        _row(cnpj="b", data_inicio_atividade=date(2026, 2, 15), situacao_cadastral=2),
        _row(
            cnpj="c",
            situacao_cadastral=8,
            data_situacao_cadastral=date(2026, 2, 20),
            data_inicio_atividade=date(2020, 1, 1),
        ),
        _row(
            cnpj="d",
            situacao_cadastral=8,
            data_situacao_cadastral=date(2026, 5, 1),
            data_inicio_atividade=date(2020, 1, 1),
        ),
    ]
    out = contar_eventos_oferta(
        rows, as_of=as_of, bairro_norm="PERDIZES", gate_fn=lambda r: True
    )
    assert out["janela_q_label"] == "2026-Q1"
    assert out["entrantes_q"] == 1  # Feb only (Q1)
    assert out["entrantes_90d"] == 1  # Apr only (Feb 15 < as_of-90 = Mar 2)
    assert out["baixas_q"] == 1
    assert out["baixas_90d"] == 1  # May baixa
    assert out["saldo_oferta_q"] == 0  # 1-1
    assert out["entrantes_bairro_q"] == 1
    assert out["baixas_bairro_90d"] == 1


def test_pressao():
    assert pressao_oferta(-1) == "retracao"
    assert pressao_oferta(1) == "expansao"
    assert pressao_oferta(0) == "neutro"


def test_multiunidade_br():
    ativos = [
        _row(cnpj="1", cnpj_basico="AAAAAAAA"),
        _row(cnpj="2", cnpj_basico="AAAAAAAA"),
        _row(cnpj="3", cnpj_basico="BBBBBBBB"),
    ]
    multi = classificar_raizes_multiunidade(ativos)
    assert multi == {"AAAAAAAA"}
