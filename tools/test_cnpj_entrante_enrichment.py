"""Testes do enriquecimento de entrantes (nome, QSA, bairro)."""
from unittest.mock import patch

from tools.cnpj_enrichment import (
    _chamar_apollo_para_entrante,
    _pick_socio_administrador,
    aplicar_enriquecimento_entrante,
)


def test_nome_exibicao_usa_razao_sem_fantasia():
    ent = aplicar_enriquecimento_entrante(
        {
            "cnpj": "12345678000199",
            "nome_fantasia": None,
            "razao_social": "ACADEMIA EXEMPLO LTDA",
            "bairro": "Meireles",
        },
        cartao=None,
        viacep=False,
    )
    assert ent["nome_exibicao"] == "ACADEMIA EXEMPLO LTDA"
    assert ent["nome_fantasia_inferido_de"] == "razao_social"
    assert ent["dados_completos"] is True


def test_lacunas_sem_razao_e_bairro():
    ent = aplicar_enriquecimento_entrante(
        {"cnpj": "12345678000199", "nome_fantasia": "GYM X"},
        cartao=None,
        viacep=False,
    )
    assert "razao_social" in (ent.get("lacunas_contato") or [])
    assert "bairro" in (ent.get("lacunas_contato") or [])


def test_pick_socio_administrador():
    socios = [
        {"nome": "João", "qualificacao": "Sócio"},
        {"nome": "Maria", "qualificacao": "49-Socio-Administrador"},
    ]
    adm = _pick_socio_administrador(socios)
    assert adm is not None
    assert adm["nome"] == "Maria"


@patch("tools.apollo_enrichment.enriquecer_empresa_com_apollo")
def test_chamar_apollo_passa_nome_socio_qsa(mock_apollo):
    mock_apollo.return_value = {"email_direto": "maria@gym.com"}
    socio = {"nome": "MARIA SILVA"}
    out = _chamar_apollo_para_entrante("GYM LTDA", socio, cidade="Fortaleza")
    mock_apollo.assert_called_once_with(
        "GYM LTDA",
        cidade="Fortaleza",
        nome_socio_qsa="MARIA SILVA",
    )
    assert out["email_direto"] == "maria@gym.com"


def test_aplicar_socio_com_telefone_apollo():
    ent = aplicar_enriquecimento_entrante(
        {"cnpj": "12345678000199", "razao_social": "GYM LTDA", "bairro": "Centro"},
        cartao={
            "status": "ok",
            "socio_administrador": {
                "nome": "Maria Silva",
                "email_direto": "maria@gym.com",
                "telefone": "85999991234",
            },
        },
        viacep=False,
    )
    assert ent["email_socio_administrador"] == "maria@gym.com"
    assert ent["telefone_socio_administrador"] == "85999991234"
