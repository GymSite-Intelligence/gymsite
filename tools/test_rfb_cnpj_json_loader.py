import pytest

from tools.rfb_cnpj_fitness_loader import (
    assert_json_has_baixadas,
    json_row_to_estabelecimento,
)

SAMPLE_02 = {
    "cnpj": "48434433000181",
    "cnpj_basico": "48434433",
    "situacao_cadastral": "02",
    "data_situacao_cadastral": 20221027,
    "data_inicio_atividade": 20221027,
    "cnae_fiscal_principal": "9313100",
    "cnae_fiscal_secundaria": "9319199",
    "nome_fantasia": "3B CROSSTRAINING",
    "bairro": "COHAB",
    "uf": "AC",
    "municipio": "0107",
    "cep": 69980000,
    "logradouro": "THAUMATURGO",
    "numero": "427",
    "complemento": "",
}

SAMPLE_08 = {
    **SAMPLE_02,
    "cnpj": "11111111000191",
    "cnpj_basico": "11111111",
    "situacao_cadastral": "08",
    "data_situacao_cadastral": 20260315,
}


def test_json_row_maps_basico_e_situacao():
    row = json_row_to_estabelecimento(SAMPLE_02, ref_date="2026-05-01", cidade="Rio Branco")
    assert row is not None
    assert row["cnpj"] == "48434433000181"
    assert row["cnpj_basico"] == "48434433"
    assert row["situacao_cadastral"] == 2
    assert row["bairro"] == "COHAB"
    assert str(row["data_inicio_atividade"])[:10] == "2022-10-27"


def test_assert_json_has_baixadas_ok():
    assert_json_has_baixadas([SAMPLE_02, SAMPLE_08])


def test_assert_json_has_baixadas_fail():
    with pytest.raises((ValueError, SystemExit)):
        assert_json_has_baixadas([SAMPLE_02])


def test_cnpj_basico_derivado_se_ausente():
    r = {**SAMPLE_02}
    del r["cnpj_basico"]
    row = json_row_to_estabelecimento(r, ref_date="2026-05-01", cidade=None)
    assert row is not None
    assert row["cnpj_basico"] == "48434433"
