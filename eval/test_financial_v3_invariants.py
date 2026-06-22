"""Testa as invariantes V3 (Fator R + guardrail de ocupação + 6 Zonas) do
financial_consistency_eval. Gated: campos ausentes não disparam (compat golden velho)."""
from __future__ import annotations

from eval.evaluators.financial_consistency_eval import evaluate_financial_consistency


def _report(cenarios=None, posicionamento=None):
    oc = {"veredito": "", "score_top1_candidato": None}
    if cenarios is not None:
        oc["viabilidade_3_cenarios"] = cenarios
    if posicionamento is not None:
        oc["posicionamento_estrategico"] = posicionamento
    return {"output_consolidado": oc}


def _fields(res):
    return {i.get("field") for i in res.issues}


def test_ocupacao_estoura_sem_inviavel_falha():
    # Ocupação 40% > teto 15% mas viabilidade=MEDIO → deve acusar.
    r = _report(cenarios={"mid": {
        "modelo": "Mid Market", "ocupacao_pct": 0.40, "teto_ocupacao": 0.15,
        "viabilidade": "MEDIO", "receita_mensal": 230000.0, "tributos_mensal": 13800.0,
    }})
    res = evaluate_financial_consistency(r, {})
    assert "ocupacao_vs_veredito" in _fields(res)


def test_ocupacao_estoura_com_inviavel_ok():
    r = _report(cenarios={"mid": {
        "modelo": "Mid Market", "ocupacao_pct": 0.40, "teto_ocupacao": 0.15,
        "viabilidade": "INVIAVEL", "receita_mensal": 230000.0, "tributos_mensal": 13800.0,
    }})
    res = evaluate_financial_consistency(r, {})
    assert "ocupacao_vs_veredito" not in _fields(res)


def test_receita_sem_tributos_falha():
    r = _report(cenarios={"low": {
        "modelo": "Low Cost", "receita_mensal": 100000.0, "tributos_mensal": 0.0,
    }})
    res = evaluate_financial_consistency(r, {})
    assert "tributos" in _fields(res)


def test_zona_6_invalida():
    r = _report(posicionamento={"zona_percepcao": 6})
    res = evaluate_financial_consistency(r, {})
    assert "zona_percepcao" in _fields(res)


def test_zona_valida_ok():
    r = _report(posicionamento={"zona_percepcao": 4, "zona_nome": "Superação"})
    res = evaluate_financial_consistency(r, {})
    assert "zona_percepcao" not in _fields(res)


def test_report_antigo_sem_campos_nao_dispara():
    # Sem campos V3 → nenhuma invariante nova dispara (gated).
    r = _report(cenarios={"mid": {"modelo": "Mid Market", "ticket_nominal": 149.0}})
    res = evaluate_financial_consistency(r, {})
    novos = {"ocupacao_vs_veredito", "tributos", "zona_percepcao"}
    assert not (_fields(res) & novos)


if __name__ == "__main__":
    import sys
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"{len(fns)} passed")
    sys.exit(0)
