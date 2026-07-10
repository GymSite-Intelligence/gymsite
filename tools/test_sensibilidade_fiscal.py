"""Task #19 — cascata fiscal dinâmica na sensibilidade + bug do enum.

Bug latente descoberto junto: o enum sensibilidade_stress do banco nunca ganhou
'ocupacao_aluguel_mais_20pct' → o INSERT do lote inteiro falhava em silêncio e a
tabela de sensibilidade estava VAZIA em todos os runs (migration 20260710 corrige).

Aqui valida-se o motor: Fator R recalculado SOB cada stress (queda de receita
pode MELHORAR o anexo) e lucro líquido de imposto em toda linha.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _rodar(folha: float):
    from tools.financial_tools import _calcular_sensibilidade

    linhas = _calcular_sensibilidade(
        base_aluguel=20_000, base_matriculas=1_000, base_ticket=100.0,
        custos_fixos_sem_aluguel=30_000, marketing_pct=0.06, inadimplencia=0.0,
        investimento_total=1_200_000, folha_mensal=folha,
    )
    return {ln["id"]: ln for ln in linhas}


def test_lote_tem_5_stresses_incluindo_fiscal():
    por_id = _rodar(folha=20_000)
    assert set(por_id) == {
        "aluguel_mais_20pct", "matriculas_menos_30pct", "ticket_menos_15pct",
        "ocupacao_aluguel_mais_20pct", "fiscal_anexo_v",
    }


def test_stress_deduz_imposto_do_anexo_resultante():
    # folha 20k / receita 100k → Fator R 0,20 < 28% → Anexo V (15,5%).
    ln = _rodar(folha=20_000)["aluguel_mais_20pct"]
    assert ln["anexo_simples"] == "V"
    # 100.000 − (30k fixos + 24k aluguel + 6k mkt) − 15.500 tributos = 24.500
    assert ln["lucro_mensal"] == 24_500.0


def test_cascata_queda_de_receita_melhora_o_anexo():
    # Matrículas −30% → receita 70k → Fator R 20/70 = 0,286 ≥ 28% → Anexo III (6%).
    ln = _rodar(folha=20_000)["matriculas_menos_30pct"]
    assert ln["anexo_simples"] == "III"
    # 70.000 − (30k + 20k + 4,2k mkt) − 4.200 tributos = 11.600
    assert ln["lucro_mensal"] == 11_600.0


def test_stress_fiscal_forca_anexo_v_mesmo_com_folha_ok():
    # folha 30k / receita 100k → Fator R 0,30: naturalmente Anexo III…
    por_id = _rodar(folha=30_000)
    assert por_id["aluguel_mais_20pct"]["anexo_simples"] == "III"
    # …mas o stress fiscal simula a disciplina de folha escorregando (PJ):
    ln = por_id["fiscal_anexo_v"]
    assert ln["anexo_simples"] == "V"
    # 100.000 − (30k + 20k + 6k) − 15.500 = 28.500 (Anexo III seriam 38.000: −9,5pp)
    assert ln["lucro_mensal"] == 28_500.0
