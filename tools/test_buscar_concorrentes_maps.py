"""Formato 1: query tipada = link Maps; gates tipo+raio; fold acento."""
from __future__ import annotations

import tools.competitor_tools as ct
from agents_site.tools import buscar_concorrentes

_COCO = "Coc\u00f3"
_QUERY_FOLD = "academia Coco, Fortaleza - CE"


def _fake_place(title: str, address: str, *, place_id: str = "ChIJx", tipos=None) -> dict:
    return {
        "id": place_id,
        "displayName": {"text": title},
        "formattedAddress": address,
        "location": {"latitude": -3.74, "longitude": -38.48},
        "types": tipos or ["gym", "Academia"],
        "rating": 4.0,
        "userRatingCount": 10,
        "_fonte_textsearch": "searchapi_google_maps",
    }


def test_query_formato1_fold_acento_unifica_coco():
    q_accent = ct._query_formato1("academia", _COCO, "Fortaleza", "CE")
    q_plain = ct._query_formato1("academia", "Coco", "Fortaleza", "CE")
    assert q_accent == q_plain == _QUERY_FOLD
    url = ct._maps_search_url_from_query(q_accent)
    assert "Coco" in url or "coco" in url.lower()
    assert "Coc%C3%B3" not in url


def test_query_formato1_e_url_1_a_1():
    q = ct._query_formato1("academia", _COCO, "Fortaleza", "CE")
    assert q == _QUERY_FOLD
    url = ct._maps_search_url_from_query(q)
    assert url == ct._maps_search_url_from_query(_QUERY_FOLD)


def test_buscar_concorrentes_formato1_query_gates_e_url(monkeypatch):
    captured: dict = {}
    addr = f"R. X - {_COCO}, Fortaleza - CE"

    def fake_ts(query: str, **kwargs):
        captured["query"] = query
        captured["kwargs"] = kwargs
        return [
            _fake_place(f"Academia Uniq Club {_COCO}", addr, place_id="a"),
            _fake_place("Keep in shape Academia", f"R. Z - {_COCO}, Fortaleza - CE", place_id="d"),
            _fake_place("Parque Esportes", f"Av. Y - {_COCO}, Fortaleza - CE", place_id="e"),
            _fake_place("CT Greenlife", f"R. W - {_COCO}, Fortaleza - CE", place_id="f"),
            _fake_place(
                f"REK CrossFit {_COCO}",
                f"R. Y - {_COCO}, Fortaleza - CE",
                place_id="b",
                tipos=["gym", "Crossfit"],
            ),
            _fake_place("Max Forma", "Av. Z - Aldeota, Fortaleza - CE", place_id="c"),
            _fake_place(
                "S3 - Treinamento Personalizado",
                f"R. A - {_COCO}, Fortaleza - CE",
                place_id="s3",
            ),
        ]

    monkeypatch.setattr(ct, "_places_textsearch", fake_ts)
    monkeypatch.setattr(
        ct,
        "geocode_endereco",
        lambda _e: {"lat": -3.74, "lng": -38.48, "fonte_geocode": "test"},
    )
    # Sem polígono: gate = raio do centróide (coords dos fakes). Evita fallback CNPJ ao vivo.
    import tools.bairro_poligono as bp

    monkeypatch.setattr(bp, "resolver_bairro_poligono", lambda **k: None)
    import tools.concorrentes_parque_tools as cp

    monkeypatch.setattr(
        cp,
        "listar_concorrentes_parque",
        lambda *a, **k: {"status": "ok", "concorrentes": []},
    )

    out = buscar_concorrentes("Fortaleza", _COCO, "CE", "academia")
    assert captured["query"] == _QUERY_FOLD
    assert out["query"] == _QUERY_FOLD
    assert out["maps_smoke_url"] == ct._maps_search_url_from_query(out["query"])
    assert out["raio_metros"] == ct.RAIO_CONCORRENCIA_CANONICO_M == 1000
    assert out["maps_smoke_aviso"] == "lista_bruta_maps_diferente_do_total_filtrado"
    nomes = {c["nome"] for c in out["concorrentes"]}
    assert f"Academia Uniq Club {_COCO}" in nomes
    assert "Keep in shape Academia" in nomes
    assert "Parque Esportes" in nomes
    assert "CT Greenlife" in nomes
    assert "Max Forma" in nomes
    assert f"REK CrossFit {_COCO}" not in nomes
    assert "S3 - Treinamento Personalizado" not in nomes
    assert out["total_concorrentes"] == 5
    assert "crossfit" in out["exclude_aplicado"]
    assert "personalizado" in out["exclude_aplicado"]
