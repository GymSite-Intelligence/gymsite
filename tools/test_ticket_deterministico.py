"""Task #26 — determinização do ticket/inadimplência/churn (última variância do score).

Antes: benchmarks via Gemini+Search Grounding (cache 7d) sobrescreviam o catálogo —
container novo/cache expirado = ticket novo = payback/viabilidade/modelo recomendado
diferentes com o MESMO input (provado: premium 299,90→500 entre runs).
Agora: catálogo (parametros_metodologia) é a ÚNICA fonte dos três; a praça entra
como régua de confronto no A6 (confronto_ticket_praca), nunca como recálculo.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_beneficios_llm_fora_do_caminho_do_ticket():
    # Fonte da verdade: nenhuma referência aos overrides dinâmicos sobrou.
    import inspect

    from tools import financial_tools

    src = inspect.getsource(financial_tools.calcular_viabilidade_3_cenarios)
    assert "_ticket_dinamico" not in src
    assert "_inadimp_dinamica" not in src
    assert "_churn_dinamico" not in src


def test_ticket_vem_do_catalogo_e_e_estavel():
    from tools.financial_tools import TICKET_FAIXAS
    from tools.parametros_metodologia import param

    assert TICKET_FAIXAS["low"]["ticket_medio"] == param("ticket_low")
    assert TICKET_FAIXAS["premium"]["ticket_medio"] == param("ticket_premium")


def test_confronto_praca_exclui_agregador_e_calcula_mediana():
    from tools.competitor_tools import confronto_ticket_praca

    concs = [
        {"planos_precos": [
            {"plano": "Mensal Musculação", "preco_mensal": "R$ 75,00"},
            {"plano": "Gold (Wellhub)", "preco_mensal": "R$ 319,99"},  # tier — fora
        ]},
        {"planos_precos": [{"plano": "Plano Fit", "preco_mensal": "R$ 95,00"}]},
        {"planos_precos": [{"plano": "Trimestral", "preco_mensal": 120.0}]},
    ]
    conf = confronto_ticket_praca(149.90, concs)
    assert conf["n_precos"] == 3            # Wellhub excluído
    assert conf["mediana_balcao"] == 95.0
    assert conf["fora_banda"] is True       # 149,90/95 = 1,58 > 1,4


def test_confronto_dentro_da_banda_nao_alerta():
    from tools.competitor_tools import confronto_ticket_praca

    concs = [{"planos_precos": [{"plano": "Mensal", "preco_mensal": "R$ 139,90"}]}]
    conf = confronto_ticket_praca(149.90, concs)
    assert conf["fora_banda"] is False


def test_confronto_sem_precos_devolve_none():
    from tools.competitor_tools import confronto_ticket_praca

    assert confronto_ticket_praca(149.90, []) is None
    assert confronto_ticket_praca(149.90, [{"planos_precos": [
        {"plano": "Gold (Wellhub)", "preco_mensal": "R$ 319,99"}]}]) is None
