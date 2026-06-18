"""Testes determinísticos para models/pipeline_schemas.py::validar_lenient.

Sem rede, sem LLM, sem I/O externo.
"""
from __future__ import annotations

import logging
import sys
import os

# Garante que o root do projeto está no path para importar models.*
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from models.pipeline_schemas import (
    A9Output,
    AnaliseDemografica,
    InteligenciaCompetitiva,
    validar_lenient,
)


# ---------------------------------------------------------------------------
# 1. Dict parcial válido: passa e retorna o ORIGINAL (mesma identidade)
# ---------------------------------------------------------------------------

def test_dict_parcial_valido_retorna_original():
    dado = {"veredito_posicionamento": "premium", "markdown": "# Teste"}
    resultado = validar_lenient(A9Output, dado, agente="A9")
    assert resultado is dado  # mesma identidade — não coage


def test_dict_parcial_vazio_retorna_original():
    dado = {}
    resultado = validar_lenient(A9Output, dado, agente="A9")
    assert resultado is dado


def test_dict_campos_obrigatorios_ausentes_retorna_original():
    # Todos os campos são Optional — dict sem nenhum campo ainda é válido
    dado = {"gaps_identificados": ["falta musculação"]}
    resultado = validar_lenient(A9Output, dado, agente="A9")
    assert resultado is dado


# ---------------------------------------------------------------------------
# 2. Campo com tipo errado → loga mas retorna original (não levanta)
# ---------------------------------------------------------------------------

def test_tipo_errado_loga_sem_levantar(caplog):
    # gaps_identificados espera list | None — passar str deve logar divergência
    dado = {"gaps_identificados": "string errada em vez de list"}
    with caplog.at_level(logging.WARNING, logger="gymsite.schemas"):
        resultado = validar_lenient(A9Output, dado, agente="A9-test")
    # NÃO deve levantar exceção
    assert resultado is dado
    # Deve ter logado aviso com o nome do agente
    mensagens = caplog.text
    assert "A9-test" in mensagens or "divergência" in mensagens or "schema" in mensagens.lower()


def test_tipo_errado_recomendacao_ticket_lista_em_vez_de_dict(caplog):
    # recomendacao_ticket espera dict | None — lista é tipo errado
    dado = {"recomendacao_ticket": [1, 2, 3]}
    with caplog.at_level(logging.WARNING, logger="gymsite.schemas"):
        resultado = validar_lenient(A9Output, dado, agente="A9")
    assert resultado is dado


def test_analise_demografica_score_errado_retorna_original(caplog):
    # score_demografico espera float | None — string não-numérica é inválida
    dado = {"score_demografico": "alto", "codigo_ibge": 3304557}
    with caplog.at_level(logging.WARNING, logger="gymsite.schemas"):
        resultado = validar_lenient(AnaliseDemografica, dado, agente="A2")
    assert resultado is dado


# ---------------------------------------------------------------------------
# 3. Não-dict → retorna original sem levantar, loga aviso
# ---------------------------------------------------------------------------

def test_nao_dict_string_retorna_original(caplog):
    dado = "texto puro"
    with caplog.at_level(logging.WARNING, logger="gymsite.schemas"):
        resultado = validar_lenient(A9Output, dado, agente="A9")
    assert resultado is dado
    assert "não-dict" in caplog.text or "dict" in caplog.text


def test_nao_dict_none_retorna_original(caplog):
    with caplog.at_level(logging.WARNING, logger="gymsite.schemas"):
        resultado = validar_lenient(A9Output, None, agente="A9")
    assert resultado is None


def test_nao_dict_lista_retorna_original(caplog):
    dado = [{"a": 1}]
    with caplog.at_level(logging.WARNING, logger="gymsite.schemas"):
        resultado = validar_lenient(A9Output, dado, agente="A9")
    assert resultado is dado


def test_nao_dict_inteiro_retorna_original(caplog):
    with caplog.at_level(logging.WARNING, logger="gymsite.schemas"):
        resultado = validar_lenient(InteligenciaCompetitiva, 42, agente="A3b")
    assert resultado == 42


# ---------------------------------------------------------------------------
# 4. extra="allow" — campo desconhecido não quebra validação
# ---------------------------------------------------------------------------

def test_campo_extra_nao_quebra():
    dado = {
        "veredito_posicionamento": "mid",
        "campo_novo_inexistente": "valor qualquer",
        "outro_campo_extra": 999,
    }
    resultado = validar_lenient(A9Output, dado, agente="A9")
    # Schema tem extra="allow", logo não deve logar divergência nem levantar
    assert resultado is dado


def test_campo_extra_inteligencia_competitiva_nao_quebra():
    dado = {
        "nivel_saturacao": "ALTO",
        "score_concorrencia": 7.5,
        "campo_futuro": True,
    }
    resultado = validar_lenient(InteligenciaCompetitiva, dado, agente="A3b")
    assert resultado is dado


def test_campo_extra_analise_demografica_nao_quebra():
    dado = {
        "codigo_ibge": "3304557",
        "insights": ["insight1", "insight2"],
        "versao_schema": "v2",  # extra
    }
    resultado = validar_lenient(AnaliseDemografica, dado, agente="A2")
    assert resultado is dado


# ---------------------------------------------------------------------------
# 5. Retorno sempre é o dado ORIGINAL — não coage tipos mesmo quando válido
# ---------------------------------------------------------------------------

def test_nao_coage_tipos_numericos():
    # score_concorrencia espera float — int deve passar sem coagir
    dado = {"score_concorrencia": 8, "nivel_saturacao": "MEDIO"}
    resultado = validar_lenient(InteligenciaCompetitiva, dado, agente="A3b")
    assert resultado is dado
    # valor original preservado, não convertido para float
    assert isinstance(resultado["score_concorrencia"], int)
