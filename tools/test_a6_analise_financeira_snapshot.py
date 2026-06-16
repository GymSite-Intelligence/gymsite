"""
Garante a correção na fonte do A4: A6 lê a análise financeira do SNAPSHOT
determinístico (`analise_financeira_pronto`, gravado pelo after_tool_callback do
A4) em vez do echo do LLM — que o flash às vezes dropa/renomeia. O echo só
contribui `justificativa` (único campo que a tool não produz).
"""
from agents.a6_report_consolidator import _resolver_analise_financeira


_SNAP = {
    "aluguel_mensal": 9000.0,
    "aviso_metodologia_aluguel": "mediana de 3 queries",
    "aluguel_pesquisa_detalhes": {"tier": "1", "mediana_r_m2": 45.0},
    "referencia_macro_bcb": {"indice": "IVG-R"},
    "score_viabilidade": 7.5,
    "cenarios": {"low": {"custos_detalhados": {"aluguel": 9000.0}}},
}


def test_snapshot_vence_echo_flash_dropado():
    # Echo do flash perdeu TODOS os campos de aluguel (cenário real do bug) e só
    # trouxe a justificativa. O snapshot deve prevalecer nos números.
    state = {
        "analise_financeira_pronto": _SNAP,
        "analise_financeira": {"analise_financeira": {"justificativa": "bairro AB, alta renda"}},
    }
    r = _resolver_analise_financeira(state)
    assert r["aluguel_mensal"] == 9000.0
    assert r["aviso_metodologia_aluguel"] == "mediana de 3 queries"
    assert r["aluguel_pesquisa_detalhes"]["tier"] == "1"
    assert r["referencia_macro_bcb"]["indice"] == "IVG-R"
    # justificativa (LLM-only) enxertada do echo
    assert r["justificativa"] == "bairro AB, alta renda"


def test_fallback_echo_sem_snapshot():
    # Runs antigos / cache sem snapshot: cai no echo do LLM (comportamento anterior).
    state = {"analise_financeira": {"analise_financeira": {"aluguel_mensal": 5000.0}}}
    r = _resolver_analise_financeira(state)
    assert r["aluguel_mensal"] == 5000.0


def test_snapshot_sem_echo_nao_quebra():
    r = _resolver_analise_financeira({"analise_financeira_pronto": _SNAP})
    assert r["aluguel_mensal"] == 9000.0
    assert "justificativa" not in r  # tool não produz; sem echo, não inventa


def test_echo_nao_sobrescreve_justificativa_do_snapshot():
    # Se (hipoteticamente) o snapshot já tiver justificativa, o echo não a troca.
    snap = {**_SNAP, "justificativa": "da tool"}
    state = {
        "analise_financeira_pronto": snap,
        "analise_financeira": {"analise_financeira": {"justificativa": "do echo"}},
    }
    assert _resolver_analise_financeira(state)["justificativa"] == "da tool"
