"""resolver_cidade_efetiva — município da RM informado como 'bairro'.

Bug que motivou (2026-05-11): A0 trata "Eusébio" como bairro de Fortaleza;
sem a correção, A6 sugere Cocó/Papicu (Fortaleza) em vez do município vizinho.
"""
from __future__ import annotations

import pytest

from agents.a6_report_consolidator import (
    get_bairros_alternativos,
    resolver_cidade_efetiva,
)
from tools.bairro_normalize import normalizar_bairro


@pytest.mark.parametrize(
    "cidade,bairro,efetiva_esperada,corrigida",
    [
        ("Fortaleza", "Eusébio", "eusébio", True),
        ("Fortaleza", "Eusebio", "eusébio", True),  # sem acento
        ("Fortaleza", "caucaia", "caucaia", True),
        ("São Paulo", "Guarulhos", "guarulhos", True),
        ("Fortaleza", "Meireles", "Fortaleza", False),
        ("Eusébio", "Tamatanduba", "Eusébio", False),
        ("Fortaleza", "", "Fortaleza", False),
    ],
)
def test_resolver_cidade_efetiva(cidade, bairro, efetiva_esperada, corrigida):
    efetiva, foi = resolver_cidade_efetiva(cidade, bairro)
    assert foi is corrigida
    assert normalizar_bairro(efetiva) == normalizar_bairro(efetiva_esperada)


def test_eusebio_nao_herda_bairros_de_fortaleza():
    """Depois da correção, alternativas vêm do mapa de Eusébio — não Cocó/Papicu."""
    efetiva, corrigida = resolver_cidade_efetiva("Fortaleza", "Eusébio")
    assert corrigida is True

    bairros = get_bairros_alternativos(efetiva)
    nomes = " ".join(b.get("bairro", "") for b in bairros).lower()
    assert "cocó" not in nomes and "coco" not in nomes
    assert "papicu" not in nomes
    assert not any(b.get("_e_fallback") for b in bairros)


def test_fortaleza_real_ainda_sugere_coco():
    """Controle: Fortaleza + bairro real continua no mapa de Fortaleza."""
    efetiva, corrigida = resolver_cidade_efetiva("Fortaleza", "Meireles")
    assert corrigida is False
    bairros = get_bairros_alternativos(efetiva)
    nomes = " ".join(b.get("bairro", "") for b in bairros).lower()
    assert "cocó" in nomes or "coco" in nomes
