"""Migração imóveis/pontos comerciais → SearchAPI google_maps (bias ll): adapta p/ o
shape places[] consumível por _extrair_lugar; zoom derivado do raio; fallback Places."""
from unittest.mock import MagicMock, patch

import tools.maps_tools as mt


def test_raio_para_zoom():
    assert mt._raio_para_zoom(1000) == 15
    assert mt._raio_para_zoom(3000) == 14
    assert mt._raio_para_zoom(5000) == 13
    assert mt._raio_para_zoom(10000) == 12


def _mock_httpx(payload):
    resp = MagicMock(); resp.json.return_value = payload
    client = MagicMock(); client.get.return_value = resp
    cm = MagicMock(); cm.__enter__.return_value = client; cm.__exit__.return_value = False
    return cm


_FAKE = {"local_results": [
    {"place_id": "ChIJ123", "title": "Fortaleza Galpões", "address": "Av X - Cocó",
     "gps_coordinates": {"latitude": -3.74, "longitude": -38.48}, "type": "Imobiliária",
     "phone": "(85) 3000-0000", "website": "https://x.com", "reviews": 12, "rating": 4.1},
]}


def test_adapta_para_extrair_lugar(monkeypatch):
    monkeypatch.setenv("SEARCHAPI_KEY", "k")
    with patch.object(mt.httpx, "Client", return_value=_mock_httpx(_FAKE)):
        places = mt._searchapi_maps_local("galpão", -3.74, -38.48, 5000, tool_name="buscar_imoveis_texto")
    assert len(places) == 1
    # shape Places → _extrair_lugar consome sem erro
    lugar = mt._extrair_lugar(places[0])
    assert lugar["place_id"] == "ChIJ123"
    assert lugar["nome"] == "Fortaleza Galpões"
    assert lugar["telefone"] == "(85) 3000-0000"
    assert lugar["lat"] == -3.74


def test_dispatch_imoveis_fallback_places(monkeypatch):
    monkeypatch.setenv("IMOVEIS_MAPS_BACKEND", "searchapi")
    with patch.object(mt, "_searchapi_maps_local", return_value=None) as sa, \
         patch.object(mt, "get_google_maps_api_key", return_value=""), \
         patch.object(mt, "_places_cache_get", return_value=None):
        # SearchAPI None + sem key Google → Places retorna [] (sem quebrar)
        out = mt.buscar_imoveis_texto("loja", -3.74, -38.48, 5000)
    sa.assert_called_once()
    assert out == []


def test_dispatch_imoveis_empty_nao_fallback_places(monkeypatch):
    """[] = SearchAPI OK sem hit — NÃO gastar Places (5 Whys / auditoria-tools)."""
    monkeypatch.setenv("IMOVEIS_MAPS_BACKEND", "searchapi")
    with patch.object(mt, "_searchapi_maps_local", return_value=[]) as sa, \
         patch.object(mt.httpx, "Client") as client_cls, \
         patch.object(mt, "_places_cache_get", return_value=None), \
         patch.object(mt, "_places_cache_set"):
        out = mt.buscar_imoveis_texto("galpão aluguel", -3.74, -38.48, 5000)
    sa.assert_called_once()
    client_cls.assert_not_called()
    assert out == []


def test_dispatch_forca_places(monkeypatch):
    monkeypatch.setenv("IMOVEIS_MAPS_BACKEND", "places")
    with patch.object(mt, "_searchapi_maps_local") as sa, \
         patch.object(mt, "get_google_maps_api_key", return_value=""), \
         patch.object(mt, "_places_cache_get", return_value=None):
        mt.buscar_imoveis_texto("loja", -3.74, -38.48, 5000)
    sa.assert_not_called()
