"""dias vindo do LLM/ADK como str não pode quebrar max(dias, 1)."""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch

import pytest

from tools import cnpj_fitness_tools as m


def test_listar_entrantes_dias_str_nao_typeerror():
    """NVIDIA/ADK às vezes manda dias='90' — coerce pra int."""
    with patch.object(m, "_supabase_client", return_value=None):
        out = m.listar_entrantes_cnpj_fitness("Fortaleza", "CE", dias="90")  # type: ignore[arg-type]
    assert out["status"] == "indisponivel"
    assert out["dias"] == 90
    cutoff = date.fromisoformat(out["cutoff"])
    assert cutoff == date.today() - timedelta(days=90)


def test_listar_entrantes_dias_lixo_vira_default():
    with patch.object(m, "_supabase_client", return_value=None):
        out = m.listar_entrantes_cnpj_fitness("Fortaleza", "CE", dias="abc")  # type: ignore[arg-type]
    assert out["dias"] == 90


def test_as_int_dias_helper():
    assert m._as_positive_int(90, default=90) == 90
    assert m._as_positive_int("90", default=90) == 90
    assert m._as_positive_int("0", default=90) == 90
    assert m._as_positive_int(None, default=90) == 90
    assert m._as_positive_int(-5, default=90) == 90
