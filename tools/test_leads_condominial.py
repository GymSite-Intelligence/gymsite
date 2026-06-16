"""Testes Apêndice C — leads de academia condominial. Sem rede (deps injetadas)."""
from __future__ import annotations

from tools.leads_condominial_tools import _montar_lead, _prioridade, leads_academia_condominial

_OBRAS = [
    {"id_cno": "1", "ni_responsavel": "11111111000111", "nome": "INCORP A SPE",
     "area_m2": 9000, "data_inicio": "2025-06-01", "em_curso": True, "bairro": "Aldeota",
     "logradouro": "Av X", "numero_logradouro": "100", "cep": "60160000", "id_municipio_rf": "1389"},
    {"id_cno": "2", "ni_responsavel": "22222222000122", "nome": "INCORP B SPE",
     "area_m2": 4000, "data_inicio": "2025-06-01", "em_curso": True, "bairro": "Meireles"},
]


def _refino(o):
    # obra 1 tem amenidade fitness; obra 2 não
    if o["id_cno"] == "1":
        return {"amenidade_fitness": True, "empreendimento": "Tower A", "confianca": "alta",
                "fonte_tipo": "pdf_empreendimento", "instagram_url": "https://instagram.com/incorpa",
                "fonte_url": "https://incorpa.com.br/book.pdf"}
    return {"amenidade_fitness": False}


def _rfb(cnpj):
    return {"razao_social": "INCORPORADORA A LTDA",
            "socio_administrador": {"nome": "Fulano Sócio"}}


def _apollo(razao, cidade, *, nome_socio_qsa=None):
    return {"nome": "Maria Compras", "titulo": "Diretora de Suprimentos",
            "email": "maria@incorpa.com.br", "telefone": "85999990000"}


def test_montar_lead_mapeia_campos():
    lead = _montar_lead(_OBRAS[0], _refino(_OBRAS[0]), _rfb("x"), _apollo("A", "Fortaleza"), "Fortaleza", "CE")
    assert lead["cnpj"] == "11111111000111"
    assert lead["cno"] == "1"
    assert lead["segmento_operacao"] == "academia_condominial"
    assert lead["razao_social"] == "INCORPORADORA A LTDA"
    assert lead["nome_fantasia"] == "Tower A"
    assert lead["contato_cnpj"]["decisor_apollo"]["titulo"] == "Diretora de Suprimentos"
    assert lead["contato_cnpj"]["instagram_construtora"].endswith("incorpa")
    assert lead["origem"] == "demanda_futura_condominial"
    assert lead["score_match"] == 0.9


def test_prioridade_por_entrega():
    # entrega próxima → alta; distante → baixa
    assert _prioridade("2026-08") == "alta"
    assert _prioridade("2030-01") == "baixa"
    assert _prioridade(None) == "media"


def test_gate_so_amenidade_fitness_vira_lead(monkeypatch):
    from tools import demanda_futura_tools as dft
    monkeypatch.setattr(dft, "_obras_grande_porte_municipio", lambda c, u: list(_OBRAS))
    r = leads_academia_condominial(
        "Fortaleza", "CE", top_n=5, dry_run=True,
        _refino_fn=_refino, _rfb_fn=_rfb, _apollo_fn=_apollo)
    assert r["status"] == "ok"
    assert r["n"] == 1                        # só a obra 1 (com fitness)
    assert r["leads"][0]["cno"] == "1"
    assert r["upserted"] == 0                 # dry_run


def test_sem_obras_indisponivel(monkeypatch):
    from tools import demanda_futura_tools as dft
    monkeypatch.setattr(dft, "_obras_grande_porte_municipio", lambda c, u: None)
    r = leads_academia_condominial("X", "ZZ", dry_run=True, _refino_fn=_refino, _rfb_fn=_rfb, _apollo_fn=_apollo)
    assert r["status"] == "indisponivel"
