"""Testes do refino A4-grounded (Apêndice B) — grounding mockado, sem rede."""
from __future__ import annotations

import json

from tools.refino_lancamento_tools import (
    _extrair_lancamento,
    _validar_match,
    refinar_demanda_via_lancamento,
)

_OBRA = {
    "nome": "Construtora Diagonal",
    "cep": "60160000", "logradouro": "Av Santos Dumont", "numero_logradouro": "1450",
    "bairro": "Aldeota",
}


def _mock(payload: dict):
    return lambda _q: json.dumps(payload)


def test_extrai_json_com_cerca_markdown():
    txt = "```json\n{\"unidades\": 240, \"torres\": 3}\n```"
    assert _extrair_lancamento(txt)["unidades"] == 240


def test_extrai_invalido_retorna_none():
    assert _extrair_lancamento("sem json aqui") is None
    assert _extrair_lancamento("") is None


def test_match_cep_numero_alta():
    ext = {"endereco": {"cep": "60160000", "numero": "1450", "bairro": "Aldeota"}}
    assert _validar_match(_OBRA, ext) == ("alta", "cep_numero")


def test_match_construtora_bairro_media():
    ext = {"construtora": "Diagonal Engenharia", "endereco": {"bairro": "Aldeota"}}
    assert _validar_match(_OBRA, ext) == ("media", "construtora_bairro")


def test_match_sem_nada_baixa():
    ext = {"construtora": "Outra", "endereco": {"bairro": "Centro"}}
    assert _validar_match(_OBRA, ext) == ("baixa", "sem_match")


def test_refino_alta_confianca_sobrescreve_proxy():
    payload = {"empreendimento": "Cidade Jardim Tower", "construtora": "Diagonal",
               "torres": 3, "unidades": 240, "tipologia": "3+ dorm",
               "amenidades": ["piscina", "espaço fitness", "salão"],
               "url": "https://x.com/cjt",
               "endereco": {"cep": "60160000", "numero": "1450", "bairro": "Aldeota"}}
    r = refinar_demanda_via_lancamento(_OBRA, _grounding_fn=_mock(payload))
    assert r["confianca"] == "alta"
    assert r["unidades_exatas"] == 240.0          # sobrescreve proxy
    assert r["amenidade_fitness"] is True         # gatilho do lead C
    assert r["fonte_url"] == "https://x.com/cjt"   # auditável
    assert r["tipologia"] == "3+ dorm"


def test_refino_baixa_confianca_mantem_proxy():
    payload = {"construtora": "Outra Inc", "unidades": 500,
               "amenidades": [], "endereco": {"bairro": "Centro"}}
    r = refinar_demanda_via_lancamento(_OBRA, _grounding_fn=_mock(payload))
    assert r["confianca"] == "baixa"
    assert r["unidades_exatas"] is None           # NÃO sobrescreve (mantém proxy)


def test_refino_grounding_quebrado_nao_crasha():
    r = refinar_demanda_via_lancamento(_OBRA, _grounding_fn=lambda _q: "lixo")
    assert r["unidades_exatas"] is None
    assert r["confianca"] == "baixa"
