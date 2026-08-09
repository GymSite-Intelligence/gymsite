"""raio_metros str from LLM must not break buscar_concorrentes."""
from __future__ import annotations

from unittest.mock import patch

from agents_site.tools_l1_dados import buscar_concorrentes


def test_buscar_concorrentes_raio_str():
    fake = {"concorrentes": []}
    with patch("tools.competitor_tools.buscar_academias", return_value=fake) as mock_b:
        with patch("tools.competitor_tools.filtrar_concorrentes_bairro_tipo", return_value=[]):
            out = buscar_concorrentes("Fortaleza", "Cocó", "CE", raio_metros="1000")  # type: ignore[arg-type]
    assert out["total_concorrentes"] == 0
    assert mock_b.call_args[0][2] == 1000
