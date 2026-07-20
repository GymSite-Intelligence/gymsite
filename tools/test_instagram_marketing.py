"""Testes unitários — classificação de temas e diagnóstico (sem SearchAPI)."""

from tools.instagram_marketing import (
    classificar_temas_post,
    diagnosticar_posts,
    slim_posts,
)
from tools.competidor_intel_cache import calcular_metricas


def test_classificar_diario_obra():
    temas = classificar_temas_post("Dia 45 do diário de obra! Estrutura quase pronta 🏗️")
    assert "diario_obra" in temas


def test_classificar_pre_venda():
    temas = classificar_temas_post("Lista VIP de pré-venda aberta — garanta sua vaga!")
    assert "pre_venda" in temas


def test_classificar_nova_unidade_em_breve():
    temas = classificar_temas_post("Nova unidade em breve no Cocó!")
    assert "nova_unidade" in temas


def test_diagnosticar_posts_ranking():
    profile = {"followers": 10_000}
    posts = slim_posts([
        {
            "type": "reel",
            "likes": 500,
            "comments": 50,
            "iso_date": "2026-06-01T12:00:00Z",
            "caption": "Diário de obra — evolução da semana",
        },
        {
            "type": "image",
            "likes": 100,
            "comments": 10,
            "iso_date": "2026-05-01T12:00:00Z",
            "caption": "Dica de treino para glúteos",
        },
    ])
    metricas = calcular_metricas(profile, posts)
    diag = diagnosticar_posts(profile, posts, metricas=metricas)
    assert diag["tema_campeao_engajamento"] == "diario_obra"
    assert diag["top_posts"][0]["eng_abs"] == 550
    assert diag["tem_metodologia_obra"] is True
