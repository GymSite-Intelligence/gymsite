"""Golden do A8 _validar_coerencia_posicionamento — invariantes cross-agente.

Caso real 6ba4b34a (São Paulo/Vila Formosa): veredito REPROVADO, 3 cenários
INVIÁVEL, modelo_recomendado Low Cost, A9 tier Mid Market / ticket R$341 /
veredito INDETERMINADO. A cascata desencontrada que quebra credibilidade no MVP.
"""
from __future__ import annotations

from agents.a8_validator import A8ValidadorCruzado


def _state_caso_6ba4b34a() -> dict:
    return {
        "veredito": "REPROVADO",
        "modelo_recomendado": "Low Cost",
        "cenarios_financeiros": [
            {"modelo": "low", "viabilidade": "INVIAVEL", "ticket_medio": 100.0},
            {"modelo": "mid", "viabilidade": "INVIAVEL", "ticket_medio": 120.0},
            {"modelo": "premium", "viabilidade": "INVIAVEL", "ticket_medio": 299.9},
        ],
        "posicionamento_estrategico": {
            "veredito_posicionamento": "INDETERMINADO",
            "headroom_renda": {"tier_modelo_percentil": "Mid Market"},
            "recomendacao_ticket": {"ticket_recomendado": 341.49},
            "zona_percepcao": None,
        },
    }


def _tipos(v: A8ValidadorCruzado) -> str:
    return " | ".join(a.claim_relacionada for a in v.alertas)


def test_caso_real_dispara_cascata():
    v = A8ValidadorCruzado()
    v._validar_coerencia_posicionamento(_state_caso_6ba4b34a())
    claims = _tipos(v)
    # INV-1: modelo recomendado com todos inviáveis (CRITICO)
    assert any(a.severidade == "CRITICO" and "todos os cenários INVIÁVEL" in a.claim_relacionada for a in v.alertas), claims
    # INV-3: modelo A4 (low) vs tier A9 (mid)
    assert any("vs tier A9=mid" in a.claim_relacionada for a in v.alertas), claims
    # INV-4: ticket 341 fora da faixa do low (100)
    assert any("ticket A9=R$341" in a.claim_relacionada for a in v.alertas), claims
    # INV-5: indeterminado mas crava ticket/tier
    assert any("INDETERMINADO" in a.claim_relacionada for a in v.alertas), claims
    # É um caso crítico → revisar_manual
    assert any(a.severidade == "CRITICO" for a in v.alertas)


def test_relatorio_coerente_nao_dispara():
    """Aprovado, low viável, A9 low com ticket alinhado → zero alertas de posicionamento."""
    v = A8ValidadorCruzado()
    v._validar_coerencia_posicionamento({
        "veredito": "APROVADO",
        "modelo_recomendado": "Low Cost",
        "cenarios_financeiros": [
            {"modelo": "low", "viabilidade": "ALTO", "ticket_medio": 100.0},
            {"modelo": "mid", "viabilidade": "MEDIO", "ticket_medio": 120.0},
        ],
        "posicionamento_estrategico": {
            "veredito_posicionamento": "OCEANO_AZUL",
            "headroom_renda": {"tier_modelo_percentil": "Low Cost"},
            "recomendacao_ticket": {"ticket_recomendado": 110.0},
        },
    })
    assert v.alertas == [], _tipos(v)


def test_sem_posicionamento_e_noop_de_a9():
    """Sem posicionamento (A8 rodou pré-A9): valida só o que dá (modelo × cenários),
    não quebra e não inventa alertas de A9."""
    v = A8ValidadorCruzado()
    v._validar_coerencia_posicionamento({
        "veredito": "APROVADO",
        "modelo_recomendado": "Low Cost",
        "cenarios_financeiros": [
            {"modelo": "low", "viabilidade": "ALTO", "ticket_medio": 100.0},
        ],
    })
    # nenhum alerta de A9 (sem posicionamento) e o caso é coerente
    assert v.alertas == [], _tipos(v)


def test_todos_inviaveis_sem_posicionamento_ainda_pega_inv1():
    """INV-1 não depende do A9 — dispara mesmo pré-A9."""
    v = A8ValidadorCruzado()
    v._validar_coerencia_posicionamento({
        "veredito": "REPROVADO",
        "modelo_recomendado": "Low Cost",
        "cenarios_financeiros": [
            {"modelo": "low", "viabilidade": "INVIAVEL", "ticket_medio": 100.0},
            {"modelo": "mid", "viabilidade": "INVIAVEL", "ticket_medio": 120.0},
        ],
    })
    assert any(a.severidade == "CRITICO" for a in v.alertas), _tipos(v)
