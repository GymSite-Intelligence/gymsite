"""Task #14 (Etapa 2 da auditoria): memória de cálculo dos scores do Cocó
(4b211a02) como REGRESSÃO — se alguém mudar fórmula ou parâmetro, estes números
mudam e o teste avisa. Documenta também o bug corrigido: score calculado com
saturação por densidade (MEDIO) enquanto o relatório exibia SATURADO do gate."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.competitor_tools import (
    calcular_score_concorrencia,
    classificar_saturacao,
    classificar_saturacao_bairro,
)
from tools.ibge_tools import calcular_score_demografico


def test_memoria_calculo_demografico_coco():
    # pop_faixa ≥ 50k (+4) + renda 4.953 ≥ 2.500 (+4) + base 2.0 = 10.0
    assert calcular_score_demografico(60_000, 4953.0) == 10.0


def test_memoria_calculo_concorrencia_coco():
    # O 1.9 do PDF só se reproduz com MEDIO (densidade raio 3km: 10÷28,3km²).
    assert calcular_score_concorrencia(10, 4.5, "MEDIO") == 1.9
    # Com o rótulo EXIBIDO (SATURADO, do gate por contagem), a fórmula dá 0.0 —
    # era a incoerência: nota 1.9 ao lado de "SATURADO".
    assert calcular_score_concorrencia(10, 4.5, "SATURADO") == 0.0


def test_saturacao_duas_reguas_divergem_no_coco():
    # A régua de densidade dilui (10 no raio 3km = MEDIO); a de contagem no
    # bairro classifica SATURADO (≥10). O A6 agora recalcula o score após o gate.
    assert classificar_saturacao(10, 3.0) == "MEDIO"
    assert classificar_saturacao_bairro(10) == "SATURADO"


def test_score_bairro_media_simples():
    # score_bairro = média das 3 dimensões: (10 + 1.9 + 6) / 3 = 5.97 (o mini
    # mostrava 5.97; o PDF arredonda pra 6.0). Pós-fix, com score_conc 0.0 do
    # gate: (10 + 0 + 6) / 3 = 5.33 — mais conservador e coerente com SATURADO.
    assert round((10 + 1.9 + 6) / 3, 2) == 5.97
    assert round((10 + 0.0 + 6) / 3, 2) == 5.33
