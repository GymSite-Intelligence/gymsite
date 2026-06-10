"""Testes unitários — popular_times_tool (sem Playwright)."""
from tools.maps_place_id import montar_maps_url_place
from tools.popular_times_tool import (
    _RE_ARIA_MOVIMENTO_HTML,
    _cache_deve_ignorar,
    _parsear_aria_label,
    DIAS_SEMANA,
)


def test_parsear_aria_pt_br():
    label = "Movimento às 14:00: 52%."
    assert _parsear_aria_label(label) == ("14", 52)


def test_parsear_aria_en_pm():
    label = "Busy at 6 PM: 87%."
    assert _parsear_aria_label(label) == ("18", 87)


def test_parsear_aria_invalido():
    assert _parsear_aria_label("Rotas") is None


def test_cache_ignora_sem_dados_com_coords():
    dados = {"status": "sem_popular_times"}
    assert _cache_deve_ignorar(
        dados, force_refresh=False, nome="Smart Fit Neo", lat=-21.1, lng=-47.8
    )
    assert not _cache_deve_ignorar(
        dados, force_refresh=False, nome="", lat=-21.1, lng=-47.8
    )


def test_cache_force_refresh():
    dados = {"status": "ok"}
    assert _cache_deve_ignorar(
        dados, force_refresh=True, nome="x", lat=0.0, lng=0.0
    )


def test_montar_url_place_id_query():
    u = montar_maps_url_place(
        "Academia Smart Fit - Neo",
        "ChIJmXdNVzu_uZQRzWnQroPidNI",
        -21.1805,
        -47.8102,
        cidade="Ribeirão Preto",
    )
    assert "place_id:ChIJmXdNVzu_uZQRzWnQroPidNI" in u


def test_dias_semana_sete():
    assert len(DIAS_SEMANA) == 7


def test_regex_aria_movimento_no_html():
    html = '<div aria-label="Movimento às 14:00: 52%."></div>'
    found = _RE_ARIA_MOVIMENTO_HTML.findall(html)
    assert found == ["Movimento às 14:00: 52%."]
