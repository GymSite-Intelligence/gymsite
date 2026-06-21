"""Base de conhecimento (Vertex AI Search) — `buscar_conhecimento`.

Offline: monkeypatch do SearchServiceClient. Valida (1) o serving_config aponta pro
ENGINE certo (engine path + serving config `default_search`, ID via env) e (2) o
parsing dos resultados pra dict {titulo,uri,trecho} com fallback extractive→snippet.
"""
import tools.discovery_engine_tools as de


class _FakeDoc:
    def __init__(self, data):
        self.derived_struct_data = data


class _FakeResult:
    def __init__(self, data):
        self.document = _FakeDoc(data)


class _FakeResponse:
    def __init__(self, results):
        self.results = results


class _FakeClient:
    last_serving = None

    def __init__(self, **kwargs):
        pass

    def search(self, request):
        _FakeClient.last_serving = request.serving_config
        return _FakeResponse([
            _FakeResult({"title": "Metodologia", "link": "gs://kb/metodo.pdf",
                         "extractive_answers": [{"content": "Score via headroom de renda."}]}),
            _FakeResult({"link": "gs://kb/zona.pdf",
                         "snippets": [{"snippet": "Academia exige zona ZEDUS/ZOC."}]}),
            _FakeResult({"title": "Vazio", "link": "gs://kb/v.pdf"}),  # sem trecho → descartado
        ])


def _patch(monkeypatch):
    from google.cloud import discoveryengine_v1 as discoveryengine
    monkeypatch.setattr(discoveryengine, "SearchServiceClient", _FakeClient)


def test_serving_config_aponta_engine(monkeypatch):
    _patch(monkeypatch)
    monkeypatch.setenv("DISCOVERY_ENGINE_ID", "gymsite-market-app_1782013373452")
    monkeypatch.setenv("DISCOVERY_SERVING_CONFIG", "default_search")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0106729343")
    de.buscar_conhecimento("como calcula viabilidade")
    sc = _FakeClient.last_serving
    assert "/engines/gymsite-market-app_1782013373452/" in sc
    assert sc.endswith("/servingConfigs/default_search")
    assert "/dataStores/" not in sc  # NÃO é dataStore path


def test_parsing_extractive_e_snippet(monkeypatch):
    _patch(monkeypatch)
    r = de.buscar_conhecimento("regras de zona")
    assert r["n_docs"] == 2  # o 3º (sem trecho) é descartado
    assert r["resultados"][0]["titulo"] == "Metodologia"
    assert r["resultados"][0]["trecho"].startswith("Score via headroom")
    assert r["resultados"][1]["uri"] == "gs://kb/zona.pdf"
    assert "ZEDUS" in r["resultados"][1]["trecho"]
    assert "Vertex" in r["fonte"]


def test_pergunta_vazia_nao_chama_api(monkeypatch):
    _patch(monkeypatch)
    _FakeClient.last_serving = None
    r = de.buscar_conhecimento("   ")
    assert r["n_docs"] == 0 and r.get("erro") == "pergunta vazia"
    assert _FakeClient.last_serving is None  # nunca tocou a API


def test_erro_degrada_limpo(monkeypatch):
    from google.cloud import discoveryengine_v1 as discoveryengine

    class _Boom:
        def __init__(self, **k):
            pass

        def search(self, request):
            raise RuntimeError("403 PERMISSION_DENIED")

    monkeypatch.setattr(discoveryengine, "SearchServiceClient", _Boom)
    r = de.buscar_conhecimento("x")
    assert r["resultados"] == [] and "PERMISSION_DENIED" in r["erro"]


def test_compat_string_legada(monkeypatch):
    _patch(monkeypatch)
    s = de.search_market_docs("metodologia")
    assert isinstance(s, str)
    assert "Fonte [" in s and "headroom" in s
