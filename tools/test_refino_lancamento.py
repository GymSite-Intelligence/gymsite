"""Testes do refino A4-grounded (Apêndice B) — grounding mockado, sem rede."""
from __future__ import annotations

import json

from tools.refino_lancamento_tools import (
    _extrair_lancamento,
    _fonte_preferida,
    _validar_match,
    refinar_demanda_via_lancamento,
)

_OBRA = {
    "nome": "Construtora Diagonal",
    "cep": "60160000", "logradouro": "Av Santos Dumont", "numero_logradouro": "1450",
    "bairro": "Aldeota",
}

# fonte auditável padrão (domínio da incorporadora, não portal)
_FONTES = [{"uri": "https://construtoradiagonal.com.br/cidade-jardim", "titulo": "Cidade Jardim"}]


def _mock(payload: dict, fontes=None):
    return lambda _q: {"texto": json.dumps(payload), "fontes": _FONTES if fontes is None else fontes}


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


def test_fonte_preferida_evita_portal():
    fontes = [{"uri": "https://vivareal.com/x"}, {"uri": "https://construtoraz.com.br/emp"}]
    assert _fonte_preferida(fontes) == "https://construtoraz.com.br/emp"
    assert _fonte_preferida([]) is None


def test_refino_alta_match_e_fonte_sobrescreve_proxy():
    payload = {"empreendimento": "Cidade Jardim Tower", "construtora": "Diagonal",
               "torres": 3, "andares": 20, "unidades": 240, "tipologia": "3+ dorm",
               "amenidades": ["piscina", "espaço fitness", "salão"],
               "endereco": {"cep": "60160000", "numero": "1450", "bairro": "Aldeota"}}
    r = refinar_demanda_via_lancamento(_OBRA, _grounding_fn=_mock(payload))
    assert r["confianca"] == "alta"
    assert r["unidades_exatas"] == 240.0
    assert r["andares"] == 20
    assert r["auditado"] is True
    assert r["amenidade_fitness"] is True
    # fonte_url = citação REAL do grounding (incorporadora), não auto-reportada
    assert r["fonte_url"] == "https://construtoradiagonal.com.br/cidade-jardim"


def test_refino_sem_fonte_rebaixa_e_nao_sobrescreve():
    # match cep+numero seria alta, MAS sem citação de grounding → não-auditável → media.
    payload = {"construtora": "Diagonal", "unidades": 240,
               "endereco": {"cep": "60160000", "numero": "1450", "bairro": "Aldeota"}}
    r = refinar_demanda_via_lancamento(_OBRA, _grounding_fn=_mock(payload, fontes=[]))
    assert r["auditado"] is False
    assert r["confianca"] == "media"              # rebaixado de alta
    assert r["unidades_exatas"] is None           # não sobrescreve sem auditoria


def test_refino_baixa_confianca_mantem_proxy():
    payload = {"construtora": "Outra Inc", "unidades": 500,
               "amenidades": [], "endereco": {"bairro": "Centro"}}
    r = refinar_demanda_via_lancamento(_OBRA, _grounding_fn=_mock(payload))
    assert r["confianca"] == "baixa"
    assert r["unidades_exatas"] is None


def test_refino_grounding_quebrado_nao_crasha():
    r = refinar_demanda_via_lancamento(_OBRA, _grounding_fn=lambda _q: {"texto": "lixo", "fontes": []})
    assert r["unidades_exatas"] is None
    assert r["confianca"] == "baixa"
