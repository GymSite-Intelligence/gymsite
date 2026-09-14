"""
Valida fix de renda municipal: Eusébio deve voltar R$ 1.835 (Censo municipal),
não R$ 870 (média UF do CE).

Também cobre:
- Município ausente do dict (fallback UF + aviso)
- Tolerância a acentos (Eusebio vs Eusébio)
- Separação per capita × domiciliar (2d9dd69)

Eram asserções no corpo do módulo: o pytest as executava na COLETA, então uma
falha aqui abortava a coleta do repositório inteiro ("Interrupted: 1 error during
collection"). Como `def test_`, a falha fica contida neste arquivo.
"""
import pytest

from tools.ibge_tools import (
    RENDA_MEDIA_UF,
    RENDA_PER_CAPITA_MUNICIPIO,
    analise_demografica_completa,
    buscar_municipio,
    buscar_renda,
)

COD_EUSEBIO = "2304285"
COD_FORTALEZA = "2304400"
RENDA_EUSEBIO_CENSO = 1835


def test_buscar_renda_eusebio_municipal():
    renda = buscar_renda(COD_EUSEBIO)
    assert renda["renda_media"] == RENDA_EUSEBIO_CENSO, (
        f"esperava R$ {RENDA_EUSEBIO_CENSO}, veio R$ {renda['renda_media']}"
    )
    assert renda["granularidade"] == "municipal"
    assert "Censo IBGE 2022 (per capita municipal)" in renda["fonte"]


def test_buscar_renda_fortaleza_municipal():
    renda = buscar_renda(COD_FORTALEZA)
    assert renda["renda_media"] == 1572
    assert renda["granularidade"] == "municipal"


def test_buscar_renda_codigo_fora_do_dict_cai_pra_uf_com_aviso():
    renda = buscar_renda("2300000")  # código fictício do CE
    assert renda["renda_media"] == RENDA_MEDIA_UF["CE"]
    assert renda["granularidade"] == "uf"
    assert "aviso" in renda, "fallback UF sem aviso esconde a imprecisão do dado"


def test_dict_municipal_nao_esvaziou():
    assert len(RENDA_PER_CAPITA_MUNICIPIO) >= 33


@pytest.mark.integration
def test_buscar_municipio_tolera_falta_de_acento():
    mun = buscar_municipio("Eusebio", "CE")
    assert mun is not None, "deveria achar Eusébio mesmo sem acento"
    assert mun["codigo"] == COD_EUSEBIO


@pytest.mark.integration
def test_analise_completa_eusebio_usa_renda_municipal():
    """Pipeline real: per capita municipal, não a média do CE."""
    result = analise_demografica_completa("Eusebio", "CE")

    assert result["municipio"] == "Eusébio"
    assert result["populacao_total"] == 57345
    assert result["renda_media_per_capita"] == RENDA_EUSEBIO_CENSO, (
        f"REGRESSÃO: renda voltou pra média UF! Veio {result['renda_media_per_capita']}"
    )
    assert result["renda_granularidade"] == "municipal"
    assert "renda_aviso" not in result, "não deve ter aviso quando é municipal"
    # Delta que motivou o fix: o per capita municipal supera a média estadual.
    assert result["renda_media_per_capita"] > RENDA_MEDIA_UF["CE"]


@pytest.mark.integration
def test_domiciliar_nao_recebe_o_per_capita():
    """2d9dd69 separou os dois: domiciliar REAL só existe com bloco de bairro (CKAN).

    Eusébio não tem CKAN de bairro, então None é o contrato — e trancar isso impede
    que o per capita volte a ser publicado com rótulo de domiciliar.
    """
    result = analise_demografica_completa("Eusebio", "CE")
    assert result["renda_bairro"] is None
    assert result["renda_media_domiciliar"] is None
