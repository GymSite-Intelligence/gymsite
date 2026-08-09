"""Regressões do contrato narrativo A6 após listing + MRLR."""
from __future__ import annotations

import agents.a6_report_consolidator as a6


def test_prompt_remove_regras_do_pipeline_poi_antigo() -> None:
    instruction = str(a6.report_consolidator_agent.instruction)
    assert "supermarket > car_dealer" not in instruction
    assert "sinal indireto-heurístico" not in instruction
    assert "Scores GeoScout são sinais indiretos heurísticos" not in instruction
    assert "Sinal indireto GeoScout: alertar SEMPRE" not in instruction
    assert "raio 3km" not in instruction
    assert "raio de 1 km do centróide" in instruction


def test_prompt_nao_duplica_bairros_hardcoded_nem_heuristica_crowdsource() -> None:
    instruction = str(a6.report_consolidator_agent.instruction)
    assert "Fortaleza CE:" not in instruction
    assert '"indicações da comunidade", "formulário", "campanha"' not in instruction
    assert "bairros_indicados" in instruction


def test_renderizador_crowdsource_existe() -> None:
    assert callable(getattr(a6, "_renderizar_secao_crowdsource", None))


def test_crowdsource_usa_lista_estruturada_e_preserva_ordem() -> None:
    state = {
        "input_params": {
            "bairros_indicados": ["Centro", "São Geraldo", "Centro", "  "]
        }
    }
    markdown = a6._renderizar_secao_crowdsource(state)
    assert "SEÇÃO PRÉ-COMPUTADA — DEMANDA SOCIAL" in markdown
    assert markdown.index("Centro") < markdown.index("São Geraldo")
    assert markdown.count("Centro") == 1


def test_crowdsource_ignora_heuristica_textual_e_lista_vazia() -> None:
    assert a6._renderizar_secao_crowdsource(
        {"input_params": {"bairros_indicados": []}, "mensagem": "campanha e votação"}
    ) == ""
    assert a6._renderizar_secao_crowdsource(
        {"bairros_indicados": ["Não deve ser lido"]}
    ) == ""


def test_bairros_indicados_canonicos_preservam_lista_estruturada() -> None:
    state = {
        "input_params": {
            "bairros_indicados": ["Industrial", "São Geraldo", "Industrial", ""]
        }
    }
    assert a6._bairros_indicados_do_state(state) == [
        "Industrial",
        "São Geraldo",
    ]
