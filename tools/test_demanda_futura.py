"""Testes Fase B — demanda futura datada (Apêndice B). Núcleo puro, sem rede.

Regra de ouro: o teste também não hardcoda — lê os fatores de param().
"""
from __future__ import annotations

from tools.demanda_futura_tools import (
    _confianca,
    _entrega_no_futuro,
    _meses_para_entrega,
    _perfil_renda_bairro,
    demanda_futura_datada,
    estimar_demanda_obra,
)
from tools.demografia_bairro_tools import classificar_perfil_bairro
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


def test_classificar_perfil_bairro_deriva_da_renda():
    # IDH-Renda alto (ex.: Cocó 0,89) → A/B por idh (alta confiança)
    alto = classificar_perfil_bairro(renda_media_pc=None, idh_renda=0.89)
    assert alto["perfil"] == "ab" and alto["base"] == "idh_renda" and alto["confianca"] == "alta"
    # Sem IDH mas renda pc acima do corte → A/B por renda (média confiança)
    renda = classificar_perfil_bairro(renda_media_pc=param("perfil_ab_renda_pc_min") + 1, idh_renda=None)
    assert renda["perfil"] == "ab" and renda["base"] == "renda_per_capita"
    # Renda baixa → geral
    baixo = classificar_perfil_bairro(renda_media_pc=900.0, idh_renda=0.55)
    assert baixo["perfil"] == "geral" and baixo["base"] == "renda_abaixo_ab"
    # Sem dado nenhum → geral fallback rotulado (baixa confiança)
    vazio = classificar_perfil_bairro()
    assert vazio["perfil"] == "geral" and vazio["base"] == "sem_dado_renda" and vazio["confianca"] == "baixa"


def test_perfil_renda_bairro_auto_deriva_via_demo_fn():
    # _demo_fn injetável → testa sem rede. Bairro alta renda vira "ab".
    def fake_demo(cidade, uf, bairro, *, id_municipio=None):
        return {"renda_media": 2500.0, "idh_renda": 0.89}
    perfil, meta = _perfil_renda_bairro("Fortaleza", "CE", "Cocó", [{"id_municipio": "2304400"}], fake_demo)
    assert perfil == "ab" and meta["base"] == "idh_renda"
    # Bairro sem renda → geral
    perfil2, meta2 = _perfil_renda_bairro("X", "CE", "Y", [{}], lambda *a, **k: {"renda_media": None, "idh_renda": None})
    assert perfil2 == "geral" and meta2["base"] == "sem_dado_renda"


def test_market_share_explicito_do_a4():
    e = estimar_demanda_obra(40_000, market_share=0.30)
    assert e["fatores_usados"]["market_share"]["fonte"] == "A4/anéis"


def test_ocupacao_censo_e_fonte_param_e_fallback():
    """Censo 2022 (média moradores) é a FONTE da ocupação; param só fallback rotulado."""
    com_censo = estimar_demanda_obra(40_000, unidades_exatas=100, ocupacao_censo=2.67)
    sem_censo = estimar_demanda_obra(40_000, unidades_exatas=100)
    # Censo manda: moradores = unidades × média_moradores do bairro (real, não param)
    assert abs(com_censo["moradores_est"] - 100 * 2.67) < 0.5
    assert "Censo 2022" in com_censo["fatores_usados"]["ocupacao"]["fonte"]
    # sem Censo → param, rotulado como fallback
    assert "fallback" in (sem_censo["fatores_usados"]["ocupacao"].get("nota") or "")
    # ocupação do Censo (2.67) ≠ ocupação default do param → moradores diferentes
    assert com_censo["moradores_est"] != sem_censo["moradores_est"]


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


def test_detalhada_aplica_refino_top_n(monkeypatch):
    from tools import demanda_futura_tools as dft

    obras = [
        {"area_m2": 9000, "data_inicio": "2025-06-01", "em_curso": True,
         "nome": "Construtora A", "bairro": "Aldeota"},
        {"area_m2": 3000, "data_inicio": "2025-06-01", "em_curso": True,
         "nome": "Construtora B", "bairro": "Aldeota"},
    ]
    monkeypatch.setattr(dft, "_obras_grande_porte_municipio", lambda c, u: obras)

    def fake_refino(o):
        if o["nome"] == "Construtora A":
            return {"unidades_exatas": 300.0, "tipologia": "3+ dorm", "amenidade_fitness": True,
                    "fonte_url": "http://x", "confianca": "alta", "empreendimento": "Tower A"}
        return {"unidades_exatas": None, "confianca": "baixa", "empreendimento": None}

    r = dft.demanda_futura_detalhada("Fortaleza", "CE", top_n=5, _refino_fn=fake_refino, _censo_fn=lambda *a, **k: None)
    assert r["status"] == "ok" and r["n_obras"] == 2
    linha_a = next(l for l in r["obras"] if l["construtora"] == "Construtora A")
    assert linha_a["unidades_est"] == 300.0                  # refino sobrescreveu proxy
    assert linha_a["unidades_fonte"] == "lancamento_exato"
    assert linha_a["confianca"] == "alta" and linha_a["amenidade_fitness"] is True


def test_classificacao_residencial_base_e_conservadora(monkeypatch):
    """Classificação carrega a BASE/fonte e é conservadora (sem sinal → não conta)."""
    from tools import demanda_futura_tools as dft

    obras = [
        {"area_m2": 8000, "data_inicio": "2025-06-01", "em_curso": True,
         "nome": "EDIFICIO RESERVA DO PARQUE", "bairro": "Cocó", "ni_responsavel": "111"},
        {"area_m2": 8000, "data_inicio": "2025-06-01", "em_curso": True,
         "nome": "GALPAO LOGISTICO ABC", "bairro": "Cocó"},        # comercial
        {"area_m2": 8000, "data_inicio": "2025-06-01", "em_curso": True,
         "nome": "SPE GENERICO 01 LTDA", "bairro": "Cocó"},        # sem sinal
    ]
    monkeypatch.setattr(dft, "_obras_grande_porte_municipio", lambda c, u: obras)
    r = dft.demanda_futura_detalhada("Fortaleza", "CE", top_n=0, _refino_fn=lambda o: None, _censo_fn=lambda *a, **k: None)

    by = {l["construtora"]: l for l in r["obras"]}
    assert by["EDIFICIO RESERVA DO PARQUE"]["provavel_residencial"] is True
    assert by["EDIFICIO RESERVA DO PARQUE"]["base_residencial"] == "nome_residencial"
    assert by["EDIFICIO RESERVA DO PARQUE"]["ni_responsavel"] == "111"  # CNPJ fonte
    assert by["GALPAO LOGISTICO ABC"]["base_residencial"] == "nome_comercial"
    assert by["SPE GENERICO 01 LTDA"]["provavel_residencial"] is False  # conservador
    assert by["SPE GENERICO 01 LTDA"]["base_residencial"] == "sem_sinal"
    # só 1 residencial, e o resumo diz a fonte
    assert r["provavel_residencial_n"] == 1
    assert r["residencial_por_base"]["nome_residencial"] == 1


def test_gate_residencial_exclui_nao_residencial_dos_totais(monkeypatch):
    """Prédio comercial/infra fica na lista (transparência) mas fora dos totais."""
    from tools import demanda_futura_tools as dft

    obras = [
        {"area_m2": 8000, "data_inicio": "2025-06-01", "em_curso": True,
         "nome": "EDIFICIO RESERVA DO PARQUE", "bairro": "Cocó"},   # residencial (keyword)
        {"area_m2": 8000, "data_inicio": "2025-06-01", "em_curso": True,
         "nome": "GALPAO LOGISTICO ABC", "bairro": "Cocó"},          # não-residencial
    ]
    monkeypatch.setattr(dft, "_obras_grande_porte_municipio", lambda c, u: obras)

    r = dft.demanda_futura_detalhada("Fortaleza", "CE", top_n=0, _refino_fn=lambda o: None, _censo_fn=lambda *a, **k: None)
    res = next(l for l in r["obras"] if l["construtora"] == "EDIFICIO RESERVA DO PARQUE")
    nao = next(l for l in r["obras"] if l["construtora"] == "GALPAO LOGISTICO ABC")

    assert res["provavel_residencial"] is True
    assert nao["provavel_residencial"] is False
    assert nao["captura_est"] == 0.0                       # não soma demanda
    assert res["captura_est"] > 0.0
    # total = só a residencial (mesma área → captura da residencial)
    assert r["provavel_residencial_n"] == 1
    assert abs(r["captura_total_est"] - round(res["captura_est"], 1)) < 0.5
