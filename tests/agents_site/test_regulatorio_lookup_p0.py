"""P0 Regulatório — lookups determinísticos UF→CREF e anuidade PJ.

Contrato: número/código de CREF e valor-base de anuidade vêm da tabela seedada,
nunca do LLM/RAG. CWA só nestas tabelas fechadas; valor FINAL regional continua
com status consultar_regional quando a linha não traz desconto curado.
"""
from __future__ import annotations

from datetime import date

import pytest

from tools.regulatorio_lookup import consultar_anuidade_pj_cref, resolver_cref_por_uf

UFS = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
]

TRANSICAO = {
    "AC": ("CREF8/AM-AC-RO-RR", "CREF26/AC"),
    "AP": ("CREF18/PA-AP", "CREF25/AP"),
    "RO": ("CREF8/AM-AC-RO-RR", "CREF23/RO"),
    "RR": ("CREF8/AM-AC-RO-RR", "CREF27/RR"),
    "TO": ("CREF14/GO-TO", "CREF24/TO"),
}


def test_resolver_cobre_27_ufs():
    for uf in UFS:
        r = resolver_cref_por_uf(uf)
        assert r.get("status") == "ok", uf
        assert r.get("uf") == uf
        assert r.get("cref_registro"), uf
        assert "CREF" in r["cref_registro"]


def test_paraiba_cref10_nao_depende_de_rag():
    r = resolver_cref_por_uf("PB")
    assert r["cref_registro"] == "CREF10/PB"
    assert r["em_transicao"] is False
    cit = r["citacao"]
    assert cit["valor"] == "CREF10/PB"
    assert "CONFEF" in cit["fonte"] or "mapa" in cit["fonte"].lower()
    assert cit["janela"]


def test_maranhao_cref21_nao_cref15():
    r = resolver_cref_por_uf("MA")
    assert r["cref_registro"] == "CREF21/MA"
    assert "CREF15" not in r["cref_registro"]


def test_sergipe_cref20_nao_ba_se():
    r = resolver_cref_por_uf("SE")
    assert r["cref_registro"] == "CREF20/SE"


@pytest.mark.parametrize(
    "uf,hoje,futuro",
    [(uf, h, f) for uf, (h, f) in TRANSICAO.items()],
)
def test_transicao_hoje_usa_cref_pai(uf, hoje, futuro):
    r = resolver_cref_por_uf(uf, data_ref="2026-07-22")
    assert r["em_transicao"] is True
    assert r["cref_registro"] == hoje
    assert r["cref_futuro"] == futuro
    assert r["vigencia_futuro"] == "2027-01-02"
    assert "UF_EM_TRANSICAO" in r["regras_aplicadas"]
    assert "NAO_REGISTRAR_EM_CREF_INOPERANTE" in r["regras_aplicadas"]


@pytest.mark.parametrize(
    "uf,hoje,futuro",
    [(uf, h, f) for uf, (h, f) in TRANSICAO.items()],
)
def test_transicao_apos_corte_usa_cref_novo(uf, hoje, futuro):
    r = resolver_cref_por_uf(uf, data_ref="2027-01-02")
    assert r["cref_registro"] == futuro
    assert r["em_transicao"] is False
    assert "UF_EM_TRANSICAO" not in r.get("regras_aplicadas", [])


def test_uf_invalida():
    r = resolver_cref_por_uf("XX")
    assert r["status"] == "erro"
    assert r.get("cref_registro") is None


def test_normaliza_uf_minuscula_e_nome():
    assert resolver_cref_por_uf("pb")["cref_registro"] == "CREF10/PB"
    assert resolver_cref_por_uf("Paraíba")["cref_registro"] == "CREF10/PB"


def test_anuidade_base_nacional_2026():
    r = consultar_anuidade_pj_cref(uf="PB", exercicio=2026)
    assert r["status"] in ("ok", "consultar_regional")
    assert r["valor_base_centavos"] == 156_968
    assert r["exercicio"] == 2026
    cit = r["citacao"]
    assert "596/2025" in cit["fonte"]
    assert cit["janela"] == "2026"


def test_anuidade_pb_traz_nota_regional_curada():
    r = consultar_anuidade_pj_cref(uf="PB")
    assert r["cref_registro"] == "CREF10/PB"
    assert r["valor_base_centavos"] == 156_968
    assert r.get("nota_regional")
    assert "150/2025" in (r.get("fonte_regional") or "")


def test_anuidade_por_cref_codigo():
    r = consultar_anuidade_pj_cref(cref=10, exercicio=2026)
    assert r["cref_registro"].startswith("CREF10")
    assert r["valor_base_centavos"] == 156_968


def test_anuidade_cref_inoperante_redireciona_ao_pai():
    """CREF23–27 ainda não recebem registro até 02/01/2027."""
    r = consultar_anuidade_pj_cref(cref=26, exercicio=2026, data_ref="2026-07-22")
    assert r["status"] != "erro"
    assert "CREF8" in r["cref_registro"] or r.get("cref_operante")
    assert "CREF_INOPERANTE" in r.get("regras_aplicadas", []) or r.get("redirecionado_de")


def test_anuidade_exercicio_fora_da_seed():
    r = consultar_anuidade_pj_cref(uf="SP", exercicio=2099)
    assert r["status"] == "exercicio_nao_coberto"
    assert r.get("valor_base_centavos") is None


def test_data_ref_aceita_date():
    r = resolver_cref_por_uf("AC", data_ref=date(2026, 12, 31))
    assert r["cref_registro"] == "CREF8/AM-AC-RO-RR"


def test_wire_adk_e_consultor_mencionam_tools():
    """Sem importar ADK/Supabase: o contrato está nos fontes."""
    from pathlib import Path

    agent = Path("agents_site/agent.py").read_text(encoding="utf-8")
    assert "resolver_cref_por_uf" in agent
    assert "consultar_anuidade_pj_cref" in agent
    assert "tools=[resolver_cref_por_uf, consultar_anuidade_pj_cref, consultar_base_regulatoria]" in agent

    ce = Path("services/consultor/consultor_engine.py").read_text(encoding="utf-8")
    assert 'name="resolver_cref_por_uf"' in ce
    assert 'name="consultar_anuidade_pj_cref"' in ce
    assert 'nome == "resolver_cref_por_uf"' in ce
    assert 'nome == "consultar_anuidade_pj_cref"' in ce
    assert '"resolver_cref_por_uf"' in ce
    assert '"consultar_anuidade_pj_cref"' in ce
