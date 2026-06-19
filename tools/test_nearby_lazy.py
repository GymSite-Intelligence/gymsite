"""searchNearby (Places New 3km) é LAZY: descartado no default → não roda; só fallback
quando textSearch-bairro vazio. Corte de custo #2 sem mudar dado."""
import httpx
import tools.competitor_tools as ct


def _mock_base(monkeypatch, descobrir_retorno):
    monkeypatch.setattr(ct, "geocode_endereco",
                        lambda e: {"lat": -3.7482, "lng": -38.4809, "fonte_geocode": "google"})
    monkeypatch.setattr(ct, "get_google_maps_api_key", lambda: "fake-key")
    monkeypatch.setattr(ct, "_descobrir_concorrentes_bairro",
                        lambda *a, **k: descobrir_retorno)


def test_default_bairro_nao_chama_nearby(monkeypatch):
    """textSearch-bairro não-vazio → retorna ele, searchNearby NÃO roda (lazy)."""
    chamadas = {"nearby": 0}
    _mock_base(monkeypatch, [{"nome": "Max Forma", "place_id": "ChIJ1", "num_avaliacoes": 424}])

    class _C(httpx.Client):
        def post(self, url, *a, **k):
            if "searchNearby" in str(url):
                chamadas["nearby"] += 1
            raise RuntimeError("não deveria rodar")

    monkeypatch.setattr(httpx, "Client", _C)
    r = ct.buscar_academias("Cocó", "Fortaleza", uf="CE")
    assert chamadas["nearby"] == 0
    assert len(r.get("concorrentes", [])) == 1


def test_bairro_vazio_cai_no_nearby(monkeypatch):
    """textSearch-bairro VAZIO → searchNearby roda como fallback."""
    chamadas = {"nearby": 0}
    _mock_base(monkeypatch, [])  # textSearch vazio

    class _Resp:
        status_code = 200
        headers = {"content-type": "application/json"}
        def json(self):
            return {"places": []}

    class _C(httpx.Client):
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def post(self, url, *a, **k):
            if "searchNearby" in str(url):
                chamadas["nearby"] += 1
            return _Resp()

    # overpass fallback não deve quebrar — mocka vazio
    monkeypatch.setattr(ct, "_buscar_academias_overpass", lambda *a, **k: ([], {}))
    monkeypatch.setattr(httpx, "Client", _C)
    ct.buscar_academias("Cocó", "Fortaleza", uf="CE")
    assert chamadas["nearby"] == 1  # fallback rodou
