"""Testes — Censo 2022 por setor censitário (agregado no raio). Sem rede (_query_fn)."""
from __future__ import annotations

from tools.censo_setor_tools import demografia_setor_censo


def test_agrega_e_estrutura(monkeypatch):
    import tools.censo_setor_tools as m
    m._CACHE.clear()
    fake = lambda lat, lng, idm, raio: {
        "n_setores": 127, "populacao": 72453, "domicilios": 27142, "media_moradores": 2.67,
    }
    r = demografia_setor_censo(-3.7465, -38.4799, id_municipio="2304400", raio_m=1500, _query_fn=fake)
    assert r["populacao"] == 72453
    assert r["media_moradores"] == 2.67
    assert r["ano"] == 2022
    assert "Censo 2022" in r["fonte"]


def test_sem_dado_retorna_none(monkeypatch):
    import tools.censo_setor_tools as m
    m._CACHE.clear()
    r = demografia_setor_censo(-3.0, -38.0, _query_fn=lambda *a: {"populacao": None})
    assert r is None


def test_lat_lng_ausente_none():
    assert demografia_setor_censo(None, None) is None
