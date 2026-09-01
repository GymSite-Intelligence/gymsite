from pathlib import Path

import pytest

from tools.carto_hex import HexCountNotFound, load_hex_table, lookup_hex_count

SAMPLE = Path("data/carto/gym_hex_cidade.json")


def test_lookup_coco_has_count():
    table = load_hex_table(SAMPLE)
    out = lookup_hex_count(-3.7455, -38.4855, table)
    assert out["n_academias"] >= 1
    assert out["cidade"] == "Fortaleza"
    assert "n_academias" in out
    assert out["base"] == "H3 res 8 da tabela gym_hex_cidade"
    assert out["fonte"]
    assert out["gerado_em"]
    assert out["hex"]


def test_lookup_ocean_raises_without_n():
    table = load_hex_table(SAMPLE)
    with pytest.raises(HexCountNotFound):
        lookup_hex_count(0.0, 0.0, table)
