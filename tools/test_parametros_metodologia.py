"""Act-on parametros: key payback, clear_param_cache, lazy financial consts."""
from __future__ import annotations

import tools.financial_tools as ft
import tools.parametros_metodologia as pm


def test_payback_limiar_recomendavel_in_defaults():
    assert "payback_limiar_recomendavel" in pm._DEFAULTS
    assert pm.param("payback_limiar_recomendavel") == 48.0


def test_clear_param_cache_resets_override_cache():
    pm._OVERRIDE_CACHE = {"fake": {"nome": "fake", "valor": 1.0}}
    pm._OVERRIDE_CACHE_AT = 0.0
    pm.clear_param_cache()
    assert pm._OVERRIDE_CACHE is None
    assert pm._OVERRIDE_CACHE_AT is None


def test_financial_ticket_faixas_lazy_via_getattr():
    """Import não congela — getattr resolve sob demanda."""
    assert "TICKET_FAIXAS" not in ft.__dict__
    faixas = ft.TICKET_FAIXAS
    assert "low" in faixas and "mid" in faixas and "premium" in faixas
    assert faixas["mid"]["ticket_medio"] == pm.param("ticket_mid")


def test_financial_ticket_faixas_from_import():
    from tools.financial_tools import TICKET_FAIXAS

    assert TICKET_FAIXAS["low"]["ticket_medio"] == pm.param("ticket_low")
