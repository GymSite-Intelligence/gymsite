"""Chave LangCache A9 — cidade/bairro via input_params e relatorio_id único."""
from agents.a9_positioning_strategist import _a9_cache_prompt


def test_cache_prompt_uses_input_params_and_relatorio_id():
    state = {
        "relatorio_id": "91561493-79d4-4872-b148-02650188b58b",
        "input_params": {"cidade": "Fortaleza", "uf": "CE", "bairro": "Parangaba"},
        "inteligencia_competitiva": {
            "concorrentes_detalhados": [{"place_id": "ChIJ_a", "nome": "Gym A"}],
        },
    }
    key = _a9_cache_prompt(state)
    assert "91561493" in key.replace("-", "")
    assert "fortaleza" in key
    assert "parangaba" in key

    state2 = {
        **state,
        "relatorio_id": "00000000-0000-0000-0000-000000000001",
        "input_params": {"cidade": "Fortaleza", "bairro": "Meireles"},
    }
    key2 = _a9_cache_prompt(state2)
    assert key != key2
