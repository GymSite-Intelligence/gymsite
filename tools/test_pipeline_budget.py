"""Testes determinísticos para api.py::_custo_acumulado_brl e PipelineBudgetExceededError.

Sem conexão Supabase real — usa sb MOCK (classe fake com interface .table().select().eq().execute()).
"""
from __future__ import annotations

import os
import sys
import types as _types

# Stub de env vars mínimas para import do api.py
os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_KEY", "fake-key")
os.environ.setdefault("PIPELINE_MAX_CUSTO_BRL", "50.0")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import pytest


# ---------------------------------------------------------------------------
# Importar apenas as funções alvo (evita side-effects do servidor FastAPI)
# ---------------------------------------------------------------------------

def _import_targets():
    """Importa _custo_acumulado_brl e PipelineBudgetExceededError de api.py."""
    import importlib
    api = importlib.import_module("api")
    return api._custo_acumulado_brl, api.PipelineBudgetExceededError


# ---------------------------------------------------------------------------
# Fake Supabase client
# ---------------------------------------------------------------------------

class _FakeExecuteResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    """Cadeia fluente: .table().select().eq().execute()"""
    def __init__(self, data=None, raise_on_execute=False):
        self._data = data if data is not None else []
        self._raise = raise_on_execute

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def execute(self):
        if self._raise:
            raise RuntimeError("Supabase indisponível")
        return _FakeExecuteResult(self._data)


class _FakeSb:
    """Stub de supabase client com dados por tabela."""
    def __init__(self, dados_por_tabela: dict):
        # dados_por_tabela: {"tabela": [{"custo_brl": float}, ...] | Exception}
        self._dados = dados_por_tabela

    def table(self, nome: str):
        entry = self._dados.get(nome)
        if isinstance(entry, Exception) or (
            isinstance(entry, type) and issubclass(entry, Exception)
        ):
            return _FakeQuery(raise_on_execute=True)
        return _FakeQuery(data=entry or [])


# ---------------------------------------------------------------------------
# 1. Soma correta — duas tabelas com valores distintos
# ---------------------------------------------------------------------------

def test_soma_correta_duas_tabelas():
    _custo, _ = _import_targets()
    sb = _FakeSb({
        "relatorio_custos_agentes": [
            {"custo_brl": 1.25},
            {"custo_brl": 0.50},
        ],
        "relatorio_api_calls": [
            {"custo_brl": 0.30},
            {"custo_brl": 0.10},
        ],
    })
    resultado = _custo(sb, "relatorio-abc-123")
    # 1.25 + 0.50 + 0.30 + 0.10 = 2.15
    assert resultado == pytest.approx(2.15, abs=0.001)


def test_soma_apenas_agentes():
    _custo, _ = _import_targets()
    sb = _FakeSb({
        "relatorio_custos_agentes": [{"custo_brl": 4.44}],
        "relatorio_api_calls": [],
    })
    resultado = _custo(sb, "rel-1")
    assert resultado == pytest.approx(4.44, abs=0.001)


def test_soma_apenas_api_calls():
    _custo, _ = _import_targets()
    sb = _FakeSb({
        "relatorio_custos_agentes": [],
        "relatorio_api_calls": [{"custo_brl": 2.00}],
    })
    resultado = _custo(sb, "rel-2")
    assert resultado == pytest.approx(2.00, abs=0.001)


def test_soma_zero_quando_vazio():
    _custo, _ = _import_targets()
    sb = _FakeSb({
        "relatorio_custos_agentes": [],
        "relatorio_api_calls": [],
    })
    resultado = _custo(sb, "rel-empty")
    assert resultado == 0.0


def test_soma_com_none_em_custo_brl():
    """custo_brl = None deve ser tratado como 0.0 (não quebra)."""
    _custo, _ = _import_targets()
    sb = _FakeSb({
        "relatorio_custos_agentes": [
            {"custo_brl": None},
            {"custo_brl": 1.0},
        ],
        "relatorio_api_calls": [{"custo_brl": None}],
    })
    resultado = _custo(sb, "rel-none")
    assert resultado == pytest.approx(1.0, abs=0.001)


def test_soma_multiplos_agentes():
    _custo, _ = _import_targets()
    sb = _FakeSb({
        "relatorio_custos_agentes": [
            {"custo_brl": 0.01},
            {"custo_brl": 0.02},
            {"custo_brl": 0.03},
            {"custo_brl": 0.04},
        ],
        "relatorio_api_calls": [{"custo_brl": 0.05}],
    })
    resultado = _custo(sb, "rel-multi")
    # 0.01+0.02+0.03+0.04+0.05 = 0.15
    assert resultado == pytest.approx(0.15, abs=0.001)


# ---------------------------------------------------------------------------
# 2. Tabela que lança exceção → degrada graciosamente (retorna parcial)
# ---------------------------------------------------------------------------

def test_excecao_em_api_calls_retorna_parcial():
    """Falha em relatorio_api_calls não derruba — retorna só o que conseguiu de agentes."""
    _custo, _ = _import_targets()

    class _SbComFalha:
        def table(self, nome):
            if nome == "relatorio_api_calls":
                return _FakeQuery(raise_on_execute=True)
            return _FakeQuery(data=[{"custo_brl": 3.00}])

    resultado = _custo(_SbComFalha(), "rel-falha")
    assert resultado == pytest.approx(3.00, abs=0.001)


def test_excecao_em_agentes_retorna_parcial():
    """Falha em relatorio_custos_agentes não derruba — retorna só api_calls."""
    _custo, _ = _import_targets()

    class _SbComFalha:
        def table(self, nome):
            if nome == "relatorio_custos_agentes":
                return _FakeQuery(raise_on_execute=True)
            return _FakeQuery(data=[{"custo_brl": 1.50}])

    resultado = _custo(_SbComFalha(), "rel-falha2")
    assert resultado == pytest.approx(1.50, abs=0.001)


def test_excecao_em_ambas_retorna_zero():
    """Falha nas duas tabelas → 0.0 (best-effort)."""
    _custo, _ = _import_targets()

    class _SbSemNada:
        def table(self, nome):
            return _FakeQuery(raise_on_execute=True)

    resultado = _custo(_SbSemNada(), "rel-total-falha")
    assert resultado == 0.0


# ---------------------------------------------------------------------------
# 3. PipelineBudgetExceededError: mensagem contém gasto e teto
# ---------------------------------------------------------------------------

def test_budget_error_mensagem_contem_gasto_e_teto():
    _, BudgetError = _import_targets()
    err = BudgetError(gasto=12.34, teto=10.00)
    msg = str(err)
    assert "12.34" in msg
    assert "10.00" in msg


def test_budget_error_atributos():
    _, BudgetError = _import_targets()
    err = BudgetError(gasto=7.89, teto=5.00)
    assert err.gasto == pytest.approx(7.89)
    assert err.teto == pytest.approx(5.00)


def test_budget_error_e_exception():
    _, BudgetError = _import_targets()
    err = BudgetError(gasto=1.0, teto=0.5)
    assert isinstance(err, Exception)


def test_budget_error_pode_ser_raised():
    _, BudgetError = _import_targets()
    with pytest.raises(BudgetError) as exc_info:
        raise BudgetError(gasto=99.99, teto=50.00)
    assert exc_info.value.gasto == pytest.approx(99.99)
    assert "99.99" in str(exc_info.value)


def test_budget_error_valores_zero():
    _, BudgetError = _import_targets()
    err = BudgetError(gasto=0.0, teto=0.0)
    assert "0.00" in str(err)


# ---------------------------------------------------------------------------
# 4. Arredondamento: resultado tem 4 casas decimais
# ---------------------------------------------------------------------------

def test_resultado_arredondado_4_casas():
    _custo, _ = _import_targets()
    sb = _FakeSb({
        "relatorio_custos_agentes": [{"custo_brl": 1.123456789}],
        "relatorio_api_calls": [],
    })
    resultado = _custo(sb, "rel-round")
    # round(1.123456789, 4) = 1.1235
    assert resultado == pytest.approx(1.1235, abs=1e-5)
