"""Task #21 — memória de cálculo do MRLR como REGRESSÃO. Coeficientes lidos da tabela
em 2026-07-06 e versionados no fallback de catalogos.py; a conta abaixo reproduziu
EXATO o aluguel do run Cocó de 05/07 (R$ 23.733/mês). Se coeficiente ou fórmula
mudarem, estes números mudam e o teste acusa."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tools.catalogos as cat
from tools.mrlr_modelo import (
    fator_de_pib_per_capita,
    local_de_zona,
    porte_de_populacao,
    valor_unitario_mrlr,
)

_PIB_FORTALEZA = 73_000_000_000.0  # ordem de grandeza do espelho municipio_pib


def _forca_fallback(monkeypatch):
    """Testa contra o SEED versionado (independe de Supabase/rede)."""
    monkeypatch.setattr(cat, "_CACHE", {})
    monkeypatch.setenv("SUPABASE_URL", "")


def test_reproducao_coco_run_0507(monkeypatch):
    _forca_fallback(monkeypatch)
    vu = valor_unitario_mrlr(900, padrao=3, local=2, porte=4,
                             pib=_PIB_FORTALEZA, fator=1)
    assert vu is not None
    assert 26.0 <= vu <= 26.8, vu           # VU ≈ 26,37/m²
    assert abs(round(vu * 900) - 23733) <= 150  # R$ 23.733/mês do PDF de 05/07


def test_sensibilidade_area(monkeypatch):
    _forca_fallback(monkeypatch)
    vu_300 = valor_unitario_mrlr(300, 3, 2, 4, _PIB_FORTALEZA, 1)
    vu_1500 = valor_unitario_mrlr(1500, 3, 2, 4, _PIB_FORTALEZA, 1)
    assert vu_300 > vu_1500                  # área maior → R$/m² menor (ln negativo)
    assert 30 <= vu_300 <= 45
    assert 18 <= vu_1500 <= 26


def test_termo_pib_quase_nulo_em_capital_relevante_em_cidade_pequena(monkeypatch):
    _forca_fallback(monkeypatch)
    vu_capital = valor_unitario_mrlr(900, 3, 2, 4, 73e9, 1)
    vu_pequena = valor_unitario_mrlr(900, 3, 2, 1, 200e6, 1)
    assert vu_capital is not None and vu_pequena is not None
    assert vu_pequena < vu_capital           # porte menor + termo 1/PIB pesando


def test_escalas_do_fallback(monkeypatch):
    _forca_fallback(monkeypatch)
    assert porte_de_populacao(2_400_000) == 4
    assert porte_de_populacao(20_000) == 1
    assert local_de_zona("USO GERAL") == 2
    assert local_de_zona("ZEIS") == 1
    assert fator_de_pib_per_capita(27_000) == 1
    assert fator_de_pib_per_capita(60_000) == 2
