"""Hard gate: bairro set + geocode sem lat → GeocodeBairroError (não publica bundle cego)."""
from __future__ import annotations

from unittest.mock import patch

import pytest


def test_build_demografia_raises_when_geocode_has_no_lat():
    from scripts.batch.build_market_bundles import GeocodeBairroError, _build_demografia

    with patch(
        "tools.maps_tools.geocode_endereco",
        return_value={"erro": "REQUEST_DENIED"},
    ):
        with patch(
            "tools.ibge_tools.analise_demografica_completa",
            return_value={"codigo_ibge": "2304400"},
        ):
            with patch(
                "tools.bairro_renda_loader.enrich_demografia_bairro",
                side_effect=lambda b, *a, **k: b,
            ):
                with pytest.raises(GeocodeBairroError) as ei:
                    _build_demografia("Fortaleza", "Meireles", "CE")
    msg = str(ei.value).lower()
    assert "geocode_bairro" in msg or "meireles" in msg


def test_build_demografia_skips_gate_when_bairro_empty():
    from scripts.batch.build_market_bundles import _build_demografia

    with patch(
        "tools.ibge_tools.analise_demografica_completa",
        return_value={"codigo_ibge": "2304400"},
    ):
        with patch(
            "tools.bairro_renda_loader.enrich_demografia_bairro",
            side_effect=lambda b, *a, **k: b,
        ):
            with patch("tools.maps_tools.geocode_endereco") as geo:
                out = _build_demografia("Fortaleza", "", "CE")
    geo.assert_not_called()
    assert isinstance(out, dict)
