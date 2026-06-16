"""Testes — descoberta de concorrentes pelo parque CNPJ. Sem rede (rows injetados)."""
from __future__ import annotations

from tools.concorrentes_parque_tools import listar_concorrentes_parque

_ROWS = [
    {"cnpj": "1", "razao_social": "ACADEMIA A LTDA", "nome_fantasia": "Smart Fit Cocó",
     "bairro": "Cocó", "logradouro": "Av X", "numero": "100", "telefone": "8530000000"},
    {"cnpj": "2", "razao_social": "STUDIO B", "nome_fantasia": "Pilates B",
     "bairro": "COCO", "logradouro": "Rua Y"},
    {"cnpj": "3", "razao_social": "GYM C", "nome_fantasia": "Fit C", "bairro": "Aldeota"},
    {"razao_social": "SEM CNPJ", "bairro": "Cocó"},  # sem cnpj → descartado
]


def test_filtra_bairro_normalizado():
    r = listar_concorrentes_parque("Fortaleza", "CE", "Cocó", _rows_fn=lambda c, u: list(_ROWS))
    assert r["status"] == "ok"
    # Cocó e COCO casam (normalizado); Aldeota fora; sem-cnpj descartado
    assert r["n"] == 2
    cnpjs = {c["cnpj"] for c in r["concorrentes"]}
    assert cnpjs == {"1", "2"}


def test_mapeia_campos():
    r = listar_concorrentes_parque("Fortaleza", "CE", "Cocó", _rows_fn=lambda c, u: list(_ROWS))
    a = next(c for c in r["concorrentes"] if c["cnpj"] == "1")
    assert a["nome"] == "Smart Fit Cocó"
    assert a["endereco"] == "Av X 100"
    assert a["fonte"] == "cnpj_parque"


def test_sem_bairro_lista_municipio_todo():
    r = listar_concorrentes_parque("Fortaleza", "CE", None, _rows_fn=lambda c, u: list(_ROWS))
    assert r["n"] == 3  # todos com cnpj (Cocó, COCO, Aldeota), sem o sem-cnpj


def test_fonte_indisponivel():
    r = listar_concorrentes_parque("X", "ZZ", "Y", _rows_fn=lambda c, u: None)
    assert r["status"] == "indisponivel"
