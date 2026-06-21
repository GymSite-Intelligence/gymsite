"""Filtro de entrantes por bairro + tipo (célula entrantes-BAIRRO da árvore 2×2).

Bairro RFB é texto livre ("Coco"/"COCÓ"/"Cocó") → casa por bairro_em_alvo, com
fallback no logradouro. Filtrar por tipo já exclui joio. Puro, offline.
"""
from tools.cnpj_fitness_tools import _filtrar_entrantes_bairro_tipo


ENTRANTES = [
    {"nome_exibicao": "Greenlife Cocó", "bairro": "Coco", "logradouro": "Av Eng Santana",
     "segmento_operacao": "academia"},
    {"nome_exibicao": "Atlas Quiropraxia", "bairro": "Cocó", "logradouro": "Rua X",
     "segmento_operacao": "fora_familia"},
    {"nome_exibicao": "LK Personal", "bairro": "COCÓ", "logradouro": "Rua Y",
     "segmento_operacao": "personal_studio"},
    {"nome_exibicao": "Box Aldeota", "bairro": "Aldeota", "logradouro": "Rua Z",
     "segmento_operacao": "crossfit_box"},
    {"nome_exibicao": "Studio sem bairro", "bairro": "", "logradouro": "Travessa Cocó 12",
     "segmento_operacao": "studio_pilates"},
]


def test_filtra_por_bairro_variacoes_de_caixa_acento():
    r = _filtrar_entrantes_bairro_tipo(ENTRANTES, bairro="Cocó")
    nomes = {e["nome_exibicao"] for e in r}
    # Coco/Cocó/COCÓ casam; Aldeota fora
    assert "Greenlife Cocó" in nomes and "Atlas Quiropraxia" in nomes and "LK Personal" in nomes
    assert "Box Aldeota" not in nomes


def test_fallback_logradouro_quando_bairro_vazio():
    # "Studio sem bairro" tem Cocó só no logradouro → entra pelo fallback
    r = _filtrar_entrantes_bairro_tipo(ENTRANTES, bairro="Cocó")
    assert any(e["nome_exibicao"] == "Studio sem bairro" for e in r)


def test_filtro_tipo_exclui_joio():
    # bairro Cocó + tipo academia → só Greenlife (joio fora_familia e personal saem)
    r = _filtrar_entrantes_bairro_tipo(ENTRANTES, bairro="Cocó", tipo_negocio="academia")
    assert [e["nome_exibicao"] for e in r] == ["Greenlife Cocó"]


def test_tipo_sem_bairro_filtra_so_segmento():
    r = _filtrar_entrantes_bairro_tipo(ENTRANTES, tipo_negocio="crossfit_box")
    assert [e["nome_exibicao"] for e in r] == ["Box Aldeota"]


def test_sem_filtros_passa_tudo():
    assert _filtrar_entrantes_bairro_tipo(ENTRANTES) == ENTRANTES
