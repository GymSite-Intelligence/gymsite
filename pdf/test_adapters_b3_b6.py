"""B3+B6 — merge gated no adapter PDF + modo_localizacao vias."""
from __future__ import annotations

import json
from pathlib import Path

from pdf.adapters import (
    merge_competidores_praca,
    relatorio_from_nested_json,
    resolver_modo_localizacao,
)


def _coco():
    p = Path("metrics/relatorios/rpt_1786416027.json")
    return json.loads(p.read_text(encoding="utf-8"))


def test_b3_merge_todos_gated_coco():
    d = _coco()
    oc = d["output_consolidado"]
    deep = oc.get("competitors_set") or []
    gated = ((oc.get("aneis_competitivos") or {}).get("cross_check") or {}).get("no_bairro") or []
    assert len(deep) == 2
    assert len(gated) == 7

    merged = merge_competidores_praca(deep, oc)
    assert len(merged) == 7
    nomes = {str(c.get("nome") or "") for c in merged}
    for g in gated:
        assert g["nome"] in nomes

    analisados = [c for c in merged if c.get("profundidade") == "analisado"]
    mapeados = [c for c in merged if c.get("profundidade") == "mapeado"]
    assert len(analisados) == 2
    assert len(mapeados) == 5


def test_b6_modo_vias_quando_top3_vazio():
    d = _coco()
    oc = d["output_consolidado"]
    assert (oc.get("top_3_candidatos") or []) == []
    assert resolver_modo_localizacao([], oc) == "vias_por_fluxo"
    assert resolver_modo_localizacao(oc.get("top_3_candidatos"), oc) == "vias_por_fluxo"


def test_b6_modo_imoveis_quando_ha_candidato():
    out = {"melhores_vias_prospeccao": {"status": "ok", "top_vias": [{"nome_via": "X"}]}}
    assert resolver_modo_localizacao([{"nome": "Loja 1"}], out) == "imoveis"


def test_b6_sem_ponto_sem_vias():
    assert resolver_modo_localizacao([], {}) == "sem_ponto"


def test_adapter_nested_coco_b3_b6():
    d = _coco()
    model = relatorio_from_nested_json(d)
    assert len(model.competidores) == 7
    assert model.metadata.get("modo_localizacao") == "vias_por_fluxo"
    assert model.metadata.get("gated_n") == 7
    assert isinstance(model.metadata.get("melhores_vias_prospeccao"), dict)
    assert model.metadata["melhores_vias_prospeccao"].get("status") == "ok"
    assert isinstance(model.metadata.get("fluxo_pedestre"), dict)
    depths = {c.profundidade for c in model.competidores}
    assert "analisado" in depths and "mapeado" in depths
    assert model.candidatos == []
