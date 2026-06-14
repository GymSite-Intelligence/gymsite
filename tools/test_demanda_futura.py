"""Testes Fase B — demanda futura datada (Apêndice B). Núcleo puro, sem rede.

Regra de ouro: o teste também não hardcoda — lê os fatores de param().
"""
from __future__ import annotations

from tools.demanda_futura_tools import (
    _confianca,
    _entrega_no_futuro,
    _meses_para_entrega,
    demanda_futura_datada,
    estimar_demanda_obra,
)
from tools.parametros_metodologia import param


def test_cadeia_pool_captura():
    # unidades → moradores → pool → captura, cada passo via param().
    e = estimar_demanda_obra(40_000, ticket_brl=149.90)
    un = 40_000 / param("m2_por_unidade")
    mor = un * param("ocupacao_default")
    pool = mor * param("penetracao_geral")
    capt = pool * param("market_share_default")
    assert abs(e["unidades_est"] - round(un, 1)) < 0.5
    assert abs(e["moradores_est"] - round(mor, 1)) < 1.0
    assert abs(e["pool_fitness_est"] - round(pool, 1)) < 1.0
    assert abs(e["captura_est"] - round(capt, 1)) < 1.0
    # captura < pool < moradores (share e penetração < 1)
    assert e["captura_est"] < e["pool_fitness_est"] < e["moradores_est"]


def test_unidades_exatas_sobrescreve_proxy():
    proxy = estimar_demanda_obra(40_000)
    exato = estimar_demanda_obra(40_000, unidades_exatas=240)
    assert exato["unidades_est"] == 240.0
    assert exato["unidades_fonte"] == "lancamento_exato"
    assert proxy["unidades_fonte"] == "proxy_area/m2"


def test_perfil_ab_aumenta_pool():
    geral = estimar_demanda_obra(40_000, perfil_bairro="geral")
    ab = estimar_demanda_obra(40_000, perfil_bairro="ab")
    assert ab["pool_fitness_est"] > geral["pool_fitness_est"]
    assert abs(ab["pool_fitness_est"] / geral["pool_fitness_est"]
               - param("penetracao_bairro_ab") / param("penetracao_geral")) < 0.02


def test_market_share_explicito_do_a4():
    e = estimar_demanda_obra(40_000, market_share=0.30)
    assert e["fatores_usados"]["market_share"]["fonte"] == "A4/anéis"


def test_fatores_carregam_fonte():
    e = estimar_demanda_obra(10_000)
    for f in ("ocupacao", "penetracao", "market_share", "inadimplencia", "ticket_brl"):
        assert e["fatores_usados"][f].get("fonte")  # nada sem fonte (regra de ouro)


def test_area_zero_nao_quebra():
    e = estimar_demanda_obra(0)
    assert e["unidades_est"] == 0.0 and e["captura_est"] == 0.0


def test_entrega_no_futuro_corta_zumbi():
    assert _entrega_no_futuro("1987-12-01", "2026-06") is False
    assert _entrega_no_futuro("2025-01-10", "2026-06") is True
    assert _entrega_no_futuro(None, "2026-06") is False


def test_meses_para_entrega_usa_param():
    # início + meses_entrega(param)
    meses = int(param("meses_entrega"))
    # 2026-01 + meses
    idx = 2026 * 12 + 0 + meses
    esperado = f"{idx // 12:04d}-{idx % 12 + 1:02d}"
    assert _meses_para_entrega("2026-01-15") == esperado


def test_confianca_declarada():
    assert _confianca(0) == "nenhuma"
    assert _confianca(1) == "baixa"
    assert _confianca(5) == "media"


def test_sem_credencial_indisponivel(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    r = demanda_futura_datada("Fortaleza", "CE")
    assert r["status"] == "indisponivel"
