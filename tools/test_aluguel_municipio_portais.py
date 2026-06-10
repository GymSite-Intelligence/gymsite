"""Testes unitários — aluguel municipal Tier 1 (sem rede)."""
from pathlib import Path

from tools.aluguel_municipio_portais import MIN_SAMPLES_ALTA
from tools.aluguel_municipio_portais import aggregate_municipio
from tools.aluguel_municipio_portais import build_portal_search_urls
from tools.aluguel_municipio_portais import parse_listings_html
from tools.aluguel_municipio_portais import _olx_ad_matches_municipio

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "aluguel_portais"


def test_build_urls_hortolandia_sp_snapshot():
    urls = build_portal_search_urls("Hortolândia", "SP", 800, 1500)
    assert "zap" in urls and "viva" in urls and "olx" in urls
    olx0 = urls["olx"][0]
    assert "/hortolandia/estado-sp" in olx0
    assert "hortolandia-e-regiao" not in olx0
    assert "estado-sp" in olx0
    assert "areaMin=800" in olx0
    assert "areaMax=1500" in olx0
    assert any("zapimoveis.com.br" in u and "hortolandia" in u for u in urls["zap"])
    assert any("vivareal.com.br/aluguel/sao-paulo/hortolandia" in u for u in urls["viva"])


def test_parse_olx_fixture():
    html = (_FIXTURES / "olx_nextdata_snippet.html").read_text(encoding="utf-8")
    samples = parse_listings_html(html, "olx", 800, 1500)
    assert len(samples) >= 1
    r_vals = [s["r_m2"] for s in samples]
    assert 10.0 <= min(r_vals) <= 30.0


def test_parse_zap_fixture():
    html = (_FIXTURES / "zap_cards_snippet.html").read_text(encoding="utf-8")
    samples = parse_listings_html(html, "zap", 800, 1500)
    assert len(samples) == 2
    assert samples[0]["portal"] == "zap"
    assert all(s["r_m2"] > 0 for s in samples)


def test_parse_viva_fixture():
    html = (_FIXTURES / "viva_cards_snippet.html").read_text(encoding="utf-8")
    samples = parse_listings_html(html, "viva", 800, 1500)
    assert len(samples) == 1
    assert samples[0]["r_m2"] == 18.5


def test_aggregate_faixa_e_confianca():
    samples = [
        {"r_m2": 15.0, "url": "https://a.example/1"},
        {"r_m2": 18.0, "url": "https://a.example/2"},
        {"r_m2": 20.0, "url": "https://a.example/3"},
        {"r_m2": 22.0, "url": "https://a.example/4"},
        {"r_m2": 25.0, "url": "https://a.example/5"},
    ]
    agg = aggregate_municipio(samples, cidade="Hortolândia", uf="SP")
    assert agg["n_validos"] == 5
    assert agg["confianca"] == "alta"
    assert agg["faixa_rs_m2"]["p25"] <= agg["faixa_rs_m2"]["mediana"] <= agg["faixa_rs_m2"]["p75"]
    assert len(agg["exemplos_urls"]) == 5
    assert agg["n_validos"] >= MIN_SAMPLES_ALTA


def test_aggregate_sem_dados_baixa_confianca():
    agg = aggregate_municipio([], cidade="X", uf="SP")
    assert agg["n_validos"] == 0
    assert agg["confianca"] == "baixa"


def test_olx_ad_matches_municipio_basic():
    ad = {
        "locationDetails": {
            "address": {
                "city": "Hortolândia",
                "state": "SP",
                "neighborhood": "Centro",
            }
        }
    }
    assert _olx_ad_matches_municipio(ad, "Hortolândia", "SP") is True


def test_olx_ad_matches_municipio_reject_other_city():
    ad = {
        "locationDetails": {
            "address": {
                "city": "São Paulo",
                "state": "SP",
                "neighborhood": "Itaim Bibi",
            }
        }
    }
    assert _olx_ad_matches_municipio(ad, "Hortolândia", "SP") is False


def test_olx_ad_matches_municipio_no_location_skips():
    ad = {"title": "Galpão comercial para aluguel"}
    assert _olx_ad_matches_municipio(ad, "Hortolândia", "SP") is False
