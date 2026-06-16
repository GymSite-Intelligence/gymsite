"""Budget guard do SearchAPI: restante REAL = allowance - usado; status por %
consumido. `remaining_credits` (pagos) é isolado e NÃO bloqueia o free tier."""
from unittest.mock import patch

from tools import searchapi_account as sa


def _acc(usado, allowance=10000, remaining=0):
    return {"_ok": True, "usage_mes": usado, "allowance_mes": allowance,
            "remaining_credits": remaining, "period_start": "x", "period_end": "y"}


def test_status_ok_abaixo_do_alerta():
    with patch.object(sa, "get_account", return_value=_acc(507)):
        r = sa.resumo_orcamento()
    assert r["status"] == "ok"
    assert r["restante"] == 9493        # allowance - usado, NÃO remaining_credits(0)
    assert r["remaining_credits_pagos"] == 0
    assert r["pct_consumido"] == 5.1


def test_remaining_credits_zero_nao_bloqueia():
    # remaining_credits=0 mas só 5% usado -> restante real 9493, status ok
    with patch.object(sa, "get_account", return_value=_acc(500, remaining=0)):
        r = sa.resumo_orcamento()
    assert r["restante"] > 0 and r["status"] == "ok"


def test_status_alerta_e_critico():
    with patch.object(sa, "get_account", return_value=_acc(8500)):
        assert sa.resumo_orcamento()["status"] == "alerta"
    with patch.object(sa, "get_account", return_value=_acc(9700)):
        assert sa.resumo_orcamento()["status"] == "critico"


def test_falha_conta_degrada():
    with patch.object(sa, "get_account", return_value={"_ok": False, "_erro": "boom"}):
        r = sa.resumo_orcamento()
    assert r["_ok"] is False and r["status"] == "desconhecido"
