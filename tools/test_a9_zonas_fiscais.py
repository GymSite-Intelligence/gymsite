"""FASE 2 (A9) — 6 Zonas de Percepção + alertas financeiros/fiscais determinísticos.

Cobre PLANO_MOTOR_FINANCEIRO_V3 §2.1 (zonas), §2.2 (FATOR_R/OCUPACAO_TICKET/KPI_BENCHMARK),
§2.4 (trava ERRC) e o schema A9Output (campos novos). Determinístico — sem LLM, sem rede.
"""
from agents.a9_positioning_strategist import (
    _alertas_financeiros_fiscais,
    _errc_deterministica,
)
from models.pipeline_schemas import A9Output
from tools.posicionamento_renda import (
    classificar_zona_percepcao,
    veredito_legado_de_zona,
)


# ── §2.1 — Zonas de Percepção nos limiares ───────────────────────────────────
def test_zona1_comodidade_ratio_baixo():
    z = classificar_zona_percepcao(0.9, "Low Cost", densidade_baixa=True, tem_gaps=True)
    assert z["zona"] == 1
    assert z["nome"] == "Comodidade"


def test_zona2_satisfacao():
    z = classificar_zona_percepcao(1.1, "Mid Market", densidade_baixa=True, tem_gaps=True)
    assert z["zona"] == 2
    assert z["nome"] == "Satisfação"


def test_zona3_resultado():
    z = classificar_zona_percepcao(1.5, "Mid Market", densidade_baixa=True, tem_gaps=True)
    assert z["zona"] == 3
    assert z["nome"] == "Resultado"


def test_zona4_superacao_ratio_alto_com_gaps():
    # ratio>=2.0 + gaps (tier não-premium) → Superação, não Excelência.
    z = classificar_zona_percepcao(2.5, "Mid Market", densidade_baixa=False, tem_gaps=True)
    assert z["zona"] == 4
    assert z["nome"] == "Superação"


def test_zona4_superacao_por_densidade_baixa_sem_gaps():
    z = classificar_zona_percepcao(2.5, "Mid Market", densidade_baixa=True, tem_gaps=False)
    assert z["zona"] == 4


def test_zona5_excelencia_premium_gaps_densidade_baixa():
    z = classificar_zona_percepcao(2.5, "Premium", densidade_baixa=True, tem_gaps=True)
    assert z["zona"] == 5
    assert z["nome"] == "Excelência"


def test_zona5_so_premium_com_gaps_e_densidade_baixa():
    # Premium mas SEM densidade baixa → não chega na Zona 5 (cai na 4).
    z = classificar_zona_percepcao(2.5, "Premium", densidade_baixa=False, tem_gaps=True)
    assert z["zona"] == 4


def test_zona6_culto_nunca_automatica():
    # Nenhuma combinação de sinais pode produzir Zona 6 automaticamente.
    for ratio in (0.5, 1.1, 1.5, 2.0, 5.0, 100.0):
        for tier in ("Low Cost", "Mid Market", "Premium"):
            for dens in (True, False):
                for gaps in (True, False):
                    z = classificar_zona_percepcao(ratio, tier, densidade_baixa=dens, tem_gaps=gaps)
                    assert z["zona"] != 6
                    assert 1 <= z["zona"] <= 5


def test_ratio_none_cai_na_zona1():
    z = classificar_zona_percepcao(None, "Premium", densidade_baixa=True, tem_gaps=True)
    assert z["zona"] == 1


# ── §2.1 — veredito legado derivado da zona ──────────────────────────────────
def test_veredito_legado_deriva_da_zona():
    assert veredito_legado_de_zona(1) == "VERMELHO"
    assert veredito_legado_de_zona(2) == "VERMELHO"
    assert veredito_legado_de_zona(3) == "TRANSICAO"
    assert veredito_legado_de_zona(4) == "OCEANO_AZUL"
    assert veredito_legado_de_zona(5) == "OCEANO_AZUL"
    assert veredito_legado_de_zona(None) is None
    assert veredito_legado_de_zona(6) is None


# ── §2.2 — alertas financeiros/fiscais ───────────────────────────────────────
def _state_a4(**cen):
    """state com analise_financeira (A4) — cenário recomendado mid."""
    base = {
        "modelo": "Mid Market", "modelo_key": "mid",
        "anexo_simples": "V", "fator_r": 0.18, "tributos_mensal": 12000.0,
        "ocupacao_pct": 0.34, "teto_ocupacao": 0.15, "ticket_piso_ocupacao": 320.0,
    }
    base.update(cen)
    return {
        "analise_financeira": {
            "recomendacao": "Mid Market",
            "cenarios": {"mid": base},
        }
    }


def test_alerta_fator_r_quando_premium():
    alertas = _alertas_financeiros_fiscais(_state_a4(), "Premium", ticket_rec=300.0)
    tipos = {a["tipo"] for a in alertas}
    assert "FATOR_R" in tipos


def test_alerta_fator_r_quando_mid():
    alertas = _alertas_financeiros_fiscais(_state_a4(), "Mid Market", ticket_rec=300.0)
    assert any(a["tipo"] == "FATOR_R" for a in alertas)


def test_sem_fator_r_em_low_cost():
    alertas = _alertas_financeiros_fiscais(_state_a4(), "Low Cost", ticket_rec=300.0)
    assert not any(a["tipo"] == "FATOR_R" for a in alertas)


def test_alerta_ocupacao_ticket_quando_ticket_menor_que_piso():
    # ticket_rec (149) < ticket_piso_ocupacao (320) → OCUPACAO_TICKET.
    alertas = _alertas_financeiros_fiscais(_state_a4(), "Mid Market", ticket_rec=149.0)
    ocup = [a for a in alertas if a["tipo"] == "OCUPACAO_TICKET"]
    assert ocup, "esperado alerta OCUPACAO_TICKET"
    assert ocup[0]["ticket_piso_ocupacao"] == 320.0


def test_sem_ocupacao_ticket_quando_ticket_acima_do_piso():
    alertas = _alertas_financeiros_fiscais(_state_a4(), "Mid Market", ticket_rec=400.0)
    assert not any(a["tipo"] == "OCUPACAO_TICKET" for a in alertas)


def test_kpi_benchmark_cac_180_e_retencao_085():
    alertas = _alertas_financeiros_fiscais(_state_a4(), "Premium", ticket_rec=300.0)
    kpi = [a for a in alertas if a["tipo"] == "KPI_BENCHMARK"]
    assert kpi, "esperado alerta KPI_BENCHMARK"
    metas = kpi[0]["metas"]
    assert metas["cac_max"] == 180.0
    assert metas["retencao_ano_min"] == 0.85
    assert metas["ltv_aluno_min"] == 2800.0  # premium
    assert metas["multiplo_ebitda"] == [3.8, 6.5]  # boutique/premium


def test_kpi_benchmark_sempre_presente_inclusive_low():
    alertas = _alertas_financeiros_fiscais(_state_a4(), "Low Cost", ticket_rec=100.0)
    assert any(a["tipo"] == "KPI_BENCHMARK" for a in alertas)


# ── A9Output aceita os campos novos ──────────────────────────────────────────
def test_a9output_aceita_campos_novos():
    out = A9Output(
        veredito_posicionamento="OCEANO_AZUL",
        zona_percepcao=5,
        zona_nome="Excelência",
        alertas_financeiros_fiscais=[{"tipo": "FATOR_R", "severidade": "ALTA"}],
    )
    assert out.zona_percepcao == 5
    assert out.zona_nome == "Excelência"
    assert out.alertas_financeiros_fiscais[0]["tipo"] == "FATOR_R"


# ── §2.4 — trava ERRC (folha protegida em Mid/Premium) ───────────────────────
def test_errc_protege_folha_em_tier_mid(monkeypatch):
    # Força avaliar_posicionamento a devolver tier Mid Market com headroom alto,
    # sem depender de Supabase/rede.
    import agents.a9_positioning_strategist as a9

    def _fake_avaliar(cidade, uf, bairro, **kw):
        return {
            "status": "ok", "veredito_posicionamento": "OCEANO_AZUL",
            "zona_percepcao": 4, "zona_nome": "Superação", "zona_descricao": "x",
            "ticket_teto_sustentavel": 300.0, "ticket_mercado": 120.0,
            "headroom_ratio": 2.5, "tier_modelo_percentil": "Mid Market",
        }

    monkeypatch.setattr(a9, "avaliar_posicionamento", _fake_avaliar, raising=False)
    # também no módulo de origem (import local dentro da função)
    import tools.posicionamento_renda as pr
    monkeypatch.setattr(pr, "avaliar_posicionamento", _fake_avaliar, raising=False)

    state = {
        "cidade": "fortaleza", "bairro": "meireles", "uf": "CE",
        "inteligencia_competitiva": {"concorrentes_detalhados": [
            {"nome": "Conc A", "planos_precos": [{"plano": "P", "inclui": ["musculação"], "preco_mensal": 120}]},
        ]},
    }
    out = _errc_deterministica(state)
    reduzir = " ".join(out["framework_errc"]["reduzir"]).lower()
    assert "proteger a folha" in reduzir
    # não deve listar corte de folha
    assert "cortar a folha" not in reduzir
