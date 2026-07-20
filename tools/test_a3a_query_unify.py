"""A3a âncora e A6 cross_check usam o MESMO termo de busca Formato 1 (search_raw hit)."""
from __future__ import annotations

import tools.competitor_tools as ct

# Fold acento: Cocó ≡ Coco → mesmo params_hash / recall SearchAPI
_QUERY_COCO = "academia no bairro Coco, Fortaleza - CE"


def test_cross_check_usa_query_formato1(monkeypatch):
    capturado = {}

    def fake_sa(query, **kwargs):
        capturado["q"] = query
        return []

    monkeypatch.setattr(ct, "_searchapi_maps_textsearch", fake_sa)
    ct.cross_check_concorrentes_bairro("Fortaleza", "CE", "Cocó", "academia")
    assert capturado["q"] == _QUERY_COCO


def test_ancora_e_cross_check_mesmo_termo(monkeypatch):
    qs = []
    monkeypatch.setattr(
        ct,
        "_places_textsearch",
        lambda q, **k: qs.append(q) or [],
    )
    monkeypatch.setattr(ct, "_searchapi_maps_textsearch", lambda q, **k: qs.append(q) or [])
    import tools.concorrentes_parque_tools as cp

    monkeypatch.setattr(
        cp,
        "listar_concorrentes_parque",
        lambda *a, **k: {"status": "ok", "concorrentes": []},
    )
    ct._descobrir_concorrentes_bairro("academia", "Cocó", "Fortaleza", "CE", -3.74, -38.49)
    ct.cross_check_concorrentes_bairro("Fortaleza", "CE", "Cocó", "academia")
    assert qs == [_QUERY_COCO, _QUERY_COCO]


def test_tipo_query_pt_removido():
    assert not hasattr(ct, "_TIPO_QUERY_PT")
