"""Teste de regressão A4 — motor fiscal (Fator R) + guardrail de ocupação (FASE 1).

Origem: PLANO_MOTOR_FINANCEIRO_V3.md §1.9. Golden case Cocó/Fortaleza, que no MVP
saía com 34,3% de ocupação e margem inflada (cegueira fiscal). Após FASE 1 o cenário
mid deve sair INVIÁVEL por estrangulamento de ocupação, com tributos > 0 (Simples
Nacional CNAE 9313-1/00) e ticket_piso_ocupacao acima do ticket recomendado.

Determinístico, sem LLM, sem rede (calcular_viabilidade_3_cenarios é só matemática).
"""
from __future__ import annotations

import pytest

from tools.financial_tools import calcular_viabilidade_3_cenarios

# Caso Cocó/Fortaleza (§1.9): area≈1150m², aluguel≈R$79.062, ticket mid R$149.
COCO_AREA_M2 = 1150.0
COCO_ALUGUEL = 79062.0


def _rodar_coco() -> dict:
    return calcular_viabilidade_3_cenarios(
        area_m2=COCO_AREA_M2,
        aluguel_mensal=COCO_ALUGUEL,
        bairro="Cocó",
        cidade="Fortaleza",
        uf="CE",
    )


def _rodar_saudavel() -> dict:
    """Caso saudável: aluguel ≈ 12% da receita do cenário mid (abaixo do teto 15%).

    Roda primeiro o Cocó p/ ler a receita mid e dimensionar um aluguel que NÃO
    estoura o teto, mantendo a mesma área/ticket.
    """
    base = _rodar_coco()
    receita_mid = float(base["cenarios"]["mid"]["receita_mensal"])
    # Aluguel = 12% da receita; condomínio (15% do aluguel) + IPTU entram na ocupação,
    # então usamos margem folgada (10% via aluguel) p/ ficar seguramente sob o teto 15%.
    aluguel_sadio = round(receita_mid * 0.10, 2)
    return calcular_viabilidade_3_cenarios(
        area_m2=COCO_AREA_M2,
        aluguel_mensal=aluguel_sadio,
        bairro="Cocó",
        cidade="Fortaleza",
        uf="CE",
    )


class TestCocoInviavelPorOcupacao:
    def setup_method(self):
        self.res = _rodar_coco()
        self.mid = self.res["cenarios"]["mid"]

    def test_ocupacao_pct_proxima_de_34pct(self):
        # §1.9 cita ~0,34 (aluguel/receita = 79062/230294 ≈ 0,343). Mas §1.4 define
        # ocupacao_abs = aluguel+condomínio+IPTU (formula seguida à risca), o que dá
        # ~0,40. Asseguramos os dois: a fração aluguel-only fica ~0,34 e a ocupação
        # cheia (a do guardrail) fica bem acima do teto mid (0,15).
        cd = self.mid["custos_detalhados"]
        aluguel_only = cd["aluguel"] / self.mid["receita_mensal"]
        assert aluguel_only == pytest.approx(0.34, abs=0.02)
        assert self.mid["ocupacao_pct"] == pytest.approx(0.40, abs=0.05)
        assert self.mid["ocupacao_pct"] > self.mid["teto_ocupacao"]

    def test_ocupacao_estoura(self):
        assert self.mid["ocupacao_estoura"] is True

    def test_veredito_mid_inviavel(self):
        # 1.5 — ocupação acima do teto rebaixa o veredito p/ INVIAVEL.
        assert self.mid["viabilidade"] == "INVIAVEL"

    def test_tributos_positivos(self):
        # 1.3 — motor fiscal: tributos > 0 e anexo definido.
        assert self.mid["tributos_mensal"] > 0
        assert self.mid["anexo_simples"] in ("III", "V")
        assert self.mid["aliquota_tributos"] > 0

    def test_ticket_piso_ocupacao_acima_do_recomendado(self):
        # 1.4 — ticket mínimo p/ ocupação caber no teto deve superar o ticket usado
        # (sinaliza necessidade de subir ticket / baixar área).
        assert self.mid["ticket_piso_ocupacao"] is not None
        assert self.mid["ticket_piso_ocupacao"] > self.mid["ticket_medio"]

    def test_lucro_liquido_de_imposto(self):
        # 1.3 — lucro = receita − custos − tributos (propaga em margem/payback).
        c = self.mid
        esperado = c["receita_mensal"] - c["custos_totais"] - c["tributos_mensal"]
        assert c["lucro_mensal_estimado"] == pytest.approx(round(esperado, 2), abs=1.0)

    def test_campos_compat_preservados(self):
        # Compat: campos do schema v2 não podem sumir.
        for campo in (
            "receita_mensal", "custos_totais", "lucro_mensal_estimado",
            "margem_percentual", "payback_meses", "viabilidade",
            "capacidade_maxima_alunos", "alunos_projetados",
        ):
            assert campo in self.mid

    def test_campos_novos_presentes(self):
        # 1.8 — campos novos no dict do cenário.
        for campo in (
            "tributos_mensal", "aliquota_tributos", "fator_r", "anexo_simples",
            "ocupacao_pct", "teto_ocupacao", "ticket_piso_ocupacao", "folha_pct_efetivo",
        ):
            assert campo in self.mid


class TestCasoSaudavelNaoEstoura:
    def setup_method(self):
        self.res = _rodar_saudavel()
        self.mid = self.res["cenarios"]["mid"]

    def test_ocupacao_nao_estoura(self):
        assert self.mid["ocupacao_estoura"] is False

    def test_mantem_viabilidade(self):
        # Caso saudável não deve sair INVIÁVEL por ocupação.
        assert self.mid["ocupacao_pct"] <= self.mid["teto_ocupacao"]


def _run_as_script() -> None:
    """Fallback quando pytest não está disponível: asserts simples + dump do caso Cocó."""
    res = _rodar_coco()
    mid = res["cenarios"]["mid"]
    print("── Caso Cocó (mid) ──")
    print(f"  ocupacao_pct        = {mid['ocupacao_pct']}")
    print(f"  ocupacao_estoura    = {mid['ocupacao_estoura']}")
    print(f"  veredito            = {mid['viabilidade']}")
    print(f"  tributos_mensal     = {mid['tributos_mensal']}")
    print(f"  anexo_simples       = {mid['anexo_simples']}")
    print(f"  aliquota_tributos   = {mid['aliquota_tributos']}")
    print(f"  ticket_medio        = {mid['ticket_medio']}")
    print(f"  ticket_piso_ocupacao= {mid['ticket_piso_ocupacao']}")
    print(f"  receita_mensal      = {mid['receita_mensal']}")
    print(f"  lucro_mensal        = {mid['lucro_mensal_estimado']}")

    assert mid["ocupacao_pct"] == pytest.approx(0.34, abs=0.05) if pytest else abs(mid["ocupacao_pct"] - 0.34) <= 0.05
    assert mid["ocupacao_estoura"] is True
    assert mid["viabilidade"] == "INVIAVEL"
    assert mid["tributos_mensal"] > 0 and mid["anexo_simples"] in ("III", "V")
    assert mid["ticket_piso_ocupacao"] is not None and mid["ticket_piso_ocupacao"] > mid["ticket_medio"]

    sadio = _rodar_saudavel()["cenarios"]["mid"]
    print("── Caso saudável (mid) ──")
    print(f"  ocupacao_pct        = {sadio['ocupacao_pct']}")
    print(f"  ocupacao_estoura    = {sadio['ocupacao_estoura']}")
    assert sadio["ocupacao_estoura"] is False
    print("\nOK — todos os asserts passaram.")


if __name__ == "__main__":
    _run_as_script()
