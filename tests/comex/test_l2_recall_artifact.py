"""L2 recall artifact — success gate vs golden importadores 9506."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RECALL = ROOT / "docs" / "comex" / "l2" / "recall_vs_golden.json"
CANDS = ROOT / "docs" / "comex" / "l2" / "candidatos_cidades_golden.json"


@pytest.mark.skipif(not RECALL.is_file(), reason="run tools/comex_l2_candidatos.py first")
def test_l2_recall_at_50_meets_v0_gate() -> None:
    data = json.loads(RECALL.read_text(encoding="utf-8"))
    r50 = data["recall_at_50"]["recall"]
    # SPEC meta v0: >= 40%; current run targets >= 80%
    assert r50 >= 0.40
    assert data["recall_at_50"]["n_golden"] == 12


@pytest.mark.skipif(not RECALL.is_file(), reason="run tools/comex_l2_candidatos.py first")
def test_l2_top_stone_is_ranked() -> None:
    data = json.loads(RECALL.read_text(encoding="utf-8"))
    by = {x["importador"]: x for x in data["por_importador"]}
    stone = by["STONE IMPORTACAO, COMERCIO ATACADISTA LTDA"]
    assert stone["found"] is True
    assert stone["rank"] is not None and stone["rank"] <= 5
    assert stone["cnpj"]


@pytest.mark.skipif(not CANDS.is_file(), reason="run tools/comex_l2_candidatos.py first")
def test_l2_candidates_carry_stamp() -> None:
    data = json.loads(CANDS.read_text(encoding="utf-8"))
    assert "NAO e comprovacao" in data["meta"]["carimbo"]
    assert data["meta"]["fonte"] == "basedosdados.br_me_cnpj"
    assert len(data["candidatos"]) >= 10
