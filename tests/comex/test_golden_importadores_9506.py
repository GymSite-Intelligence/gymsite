"""Golden fixture: Logcomex-like importadores 9506 (success definition)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

GOLDEN_DIR = Path(__file__).resolve().parents[2] / "docs" / "comex" / "golden"
RAW = GOLDEN_DIR / "importadores_9506_teus_porto_destino.json"
ROLLUP = GOLDEN_DIR / "importadores_9506_rollup.json"
META = GOLDEN_DIR / "importadores_9506_meta.json"

REQUIRED = {
    "importador",
    "total_teus",
    "pais_origem",
    "capitulo_ncm",
    "porto_origem",
    "porto_destino",
    "uf_importador",
    "cidade_importador",
    "exportador_fornecedor",
    "mes_operacao_fmt",
    "descricao_produto",
    "conteineres_20_pes",
    "conteineres_40_pes",
    "conteineres_fcl",
    "conteineres_lcl",
}


@pytest.fixture(scope="module")
def raw_rows() -> list[dict]:
    assert RAW.is_file(), f"missing golden {RAW}"
    data = json.loads(RAW.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    return data


@pytest.fixture(scope="module")
def rollup(raw_rows: list[dict]) -> list[dict]:
    assert ROLLUP.is_file()
    return json.loads(ROLLUP.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def meta() -> dict:
    assert META.is_file()
    return json.loads(META.read_text(encoding="utf-8"))


def test_golden_schema_complete(raw_rows: list[dict]) -> None:
    assert len(raw_rows) == 19
    for row in raw_rows:
        missing = REQUIRED - set(row)
        assert not missing, f"{row.get('importador')}: {missing}"
        assert isinstance(row["importador"], str) and row["importador"].strip()
        assert int(row["total_teus"]) >= 0


def test_golden_totals(raw_rows: list[dict], meta: dict, rollup: list[dict]) -> None:
    teus = sum(int(r["total_teus"]) for r in raw_rows)
    assert teus == 767
    assert meta["total_teus"] == 767
    assert meta["n_importadores"] == 12
    assert len(rollup) == 12
    assert rollup[0]["importador"].startswith("STONE")
    assert rollup[0]["total_teus"] == 282


def test_golden_focus_9506_sc(raw_rows: list[dict]) -> None:
    assert all("9506" in str(r["capitulo_ncm"]) for r in raw_rows)
    ufs = {r["uf_importador"] for r in raw_rows}
    assert "SC" in ufs
    dest = {r["porto_destino"] for r in raw_rows}
    assert "NAVEGANTES" in dest
    assert {r["mes_operacao_fmt"] for r in raw_rows} == {"07/2026"}


def test_success_names_are_nominal(rollup: list[dict]) -> None:
    """Success = named importers exist (the Stat gap we chase via candidates)."""
    names = [r["importador"] for r in rollup]
    assert len(names) == 12
    assert "LIFE FITNESS COMERCIO DE EQUIPAMENTOS DO BRASIL LTDA." in names
    assert all(r.get("importador_norm") for r in rollup)
