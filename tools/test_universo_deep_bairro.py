"""Gated no bairro entra no deep (reviews + planos) — não só o top-3."""
from tools.competitor_tools import universo_deep_bairro


def test_todos_gated_entram_mesmo_sem_registro_completo():
    gated = [
        {"place_id": f"ChIJ{i}", "nome": f"Academia {i}", "num_avaliacoes": i}
        for i in range(14)
    ]
    deep = universo_deep_bairro(
        gated_no_bairro=gated,
        candidatos_completos=[
            {"place_id": "ChIJ0", "nome": "Academia 0", "website": "https://a0.com"},
            {"place_id": "ChIJ1", "nome": "Academia 1", "website": "https://a1.com"},
            {"place_id": "ChIJ2", "nome": "Academia 2"},
        ],
        max_enriq=25,
    )
    assert len(deep) == 14
    by_id = {c["place_id"]: c for c in deep}
    assert by_id["ChIJ0"]["website"] == "https://a0.com"
    assert by_id["ChIJ7"]["nome"] == "Academia 7"
    assert by_id["ChIJ7"]["fonte_busca"] == "gate_bairro"


def test_teto_so_corta_praca_patologica():
    gated = [{"place_id": f"id{i}", "nome": f"A{i}", "num_avaliacoes": i} for i in range(30)]
    deep = universo_deep_bairro(
        gated_no_bairro=gated,
        candidatos_completos=[],
        max_enriq=25,
    )
    assert len(deep) == 25
    assert deep[0]["num_avaliacoes"] >= deep[-1]["num_avaliacoes"]


def test_dedup_por_place_id():
    gated = [
        {"place_id": "ChIJsame", "nome": "Smart Fit A"},
        {"place_id": "ChIJsame", "nome": "Smart Fit A dup"},
        {"place_id": "ChIJother", "nome": "Ideal"},
    ]
    deep = universo_deep_bairro(gated_no_bairro=gated, candidatos_completos=[], max_enriq=25)
    assert len(deep) == 2
