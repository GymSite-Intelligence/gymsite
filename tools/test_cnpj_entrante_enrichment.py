"""Testes do enriquecimento de entrantes (nome, QSA, bairro)."""
from tools.cnpj_enrichment import (
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
