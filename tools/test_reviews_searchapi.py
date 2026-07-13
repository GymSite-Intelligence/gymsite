"""Reviews do concorrente via SearchAPI google_maps_reviews: shape do card + sort
lowest_rating (dores primeiro) + topics[] + fallback Places quando vazio/sem key."""
from unittest.mock import MagicMock, patch

import tools.competitor_tools as ct


def test_processar_review_card():
    c = ct._processar_review_card("Equipamento quebrado e lotado demais", 2, "João Silva", "há 2 dias")
    assert c["rating"] == 2 and c["sentimento"] == "negativo"
    assert c["autor"] == "João Silva"
    assert len(c["quote_curta"]) <= 180


def test_map_topic_keyword_to_categoria():
    assert ct._map_topic_keyword_to_categoria("staff") == "atendimento_ruim"
    assert ct._map_topic_keyword_to_categoria("Preço mensalidade") == "preco_alto"
    assert ct._map_topic_keyword_to_categoria("knicks") == "outra"


def test_build_temas_insatisfacao_from_topics():
    topics = [{"keyword": "staff", "reviews": 12}, {"keyword": "equipment", "reviews": 8}]
    temas = ct._build_temas_insatisfacao(topics)
    assert len(temas) == 2
    assert temas[0]["categoria_dor"] == "atendimento_ruim"
    assert temas[0]["fonte"] == "searchapi_topics"


def test_classificar_dores_deterministico_review():
    conc = [{
        "place_id": "ChIJx",
        "nome": "Gym",
        "reviews": [{
            "rating": 1,
            "quote_curta": "muito cheio e equipamentos quebrados",
            "dores_detectadas": ["muito cheio", "equipamentos quebrados"],
        }],
    }]
    with patch.object(ct, "_fetch_reviews_bundle", return_value={"reviews": [], "topics": []}):
        ct.classificar_dores_reviews_deterministico(conc)
    assert conc[0]["reviews"][0]["categoria_dor"] == "lotacao"


def test_gemini_off_by_default(monkeypatch):
    monkeypatch.delenv("CLASSIFICAR_DORES_GEMINI", raising=False)
    assert ct._classificacao_dores_usa_gemini() is False


def _mock_httpx(payload):
    resp = MagicMock(); resp.json.return_value = payload
    client = MagicMock(); client.get.return_value = resp
    cm = MagicMock(); cm.__enter__.return_value = client; cm.__exit__.return_value = False
    return cm


_FAKE_REVIEWS = {
    "reviews": [
        {"text": "Só tem propaganda, cheira mal <br> péssimo", "rating": 1, "user": {"name": "Ana"}, "date": "há 1 semana"},
        {"text": "Estrutura boa porém caro", "rating": 3, "user": {"name": "Bruno"}, "date": "há 1 mês"},
    ],
    "topics": [{"keyword": "staff", "reviews": 5}],
}


def test_fetch_reviews_bundle_extracts_topics(monkeypatch):
    monkeypatch.setenv("SEARCHAPI_KEY", "k")
    ct._REVIEWS_BUNDLE_MEMO.clear()
    with patch.object(ct.httpx, "Client", return_value=_mock_httpx(_FAKE_REVIEWS)):
        bundle = ct._fetch_reviews_bundle("ChIJabc")
    assert bundle is not None
    assert len(bundle["reviews"]) == 2
    assert bundle["topics"][0]["keyword"] == "staff"


def test_reviews_searchapi_card_limpa_html(monkeypatch):
    monkeypatch.setenv("SEARCHAPI_KEY", "k")
    with patch.object(ct.httpx, "Client", return_value=_mock_httpx(_FAKE_REVIEWS)):
        out = ct._reviews_searchapi_card("ChIJabc")
    assert len(out) == 2
    assert "<br>" not in out[0]["quote_curta"] and "<" not in out[0]["quote_curta"]
    assert out[0]["rating"] == 1 and out[0]["sentimento"] == "negativo"


def test_dispatcher_usa_searchapi(monkeypatch):
    monkeypatch.setenv("COMPETIDOR_MAPS_BACKEND", "searchapi")
    fake = [{"rating": 1, "quote_curta": "ruim", "sentimento": "negativo",
             "dores_detectadas": [], "servicos_mencionados": [], "autor": "X", "data_relativa": ""}]
    with patch.object(ct, "_reviews_searchapi_card", return_value=fake):
        d = ct.buscar_reviews_academia("ChIJabc", "Tal")
    assert d["fonte_reviews"] == "searchapi" and len(d["reviews"]) == 1


def test_dispatcher_fallback_places_quando_vazio(monkeypatch):
    monkeypatch.setenv("COMPETIDOR_MAPS_BACKEND", "searchapi")
    # SearchAPI vazio + sem chave Google → cai no ramo Places e devolve erro (sem key)
    with patch.object(ct, "_reviews_searchapi_card", return_value=None), \
         patch.object(ct, "get_google_maps_api_key", return_value=""):
        d = ct.buscar_reviews_academia("ChIJabc", "Tal")
    assert "erro" in d
