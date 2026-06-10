"""Testes — parse de place_id em URLs Google Maps."""
from tools.maps_place_id import (
    extrair_kgmid_de_url,
    extrair_place_id_de_url,
    montar_maps_url_place,
)


def test_place_id_query_param():
    url = "https://www.google.com/maps/place/?q=place_id:ChIJmXdNVzu_uZQRzWnQroPidNI"
    assert extrair_place_id_de_url(url) == "ChIJmXdNVzu_uZQRzWnQroPidNI"


def test_kgmid_from_share_url():
    url = (
        "https://www.google.com/maps/place/Academia+Smart+Fit+-+Neo/@-21.18,-47.79,17z/"
        "data=!4m16!1m9!3m8!1s0x94b9bf3b574d7799:0xd274e283aed069cd"
        "!16s%2Fg%2F11c6ddhr68"
    )
    assert extrair_place_id_de_url(url) is None
    assert extrair_kgmid_de_url(url) == "g/11c6ddhr68"


def test_montar_maps_url_rica():
    u = montar_maps_url_place(
        "Smart Fit Neo", "ChIJabc", -21.19, -47.79, cidade="Ribeirão Preto"
    )
    assert "place_id:ChIJabc" in u
    assert "hl=pt-BR" in u


def test_montar_maps_url_hex():
    u = montar_maps_url_place(
        "Smart Fit Neo",
        "ChIJabc",
        -21.19,
        -47.79,
        hex_ftid="0x94b9bf3b574d7799:0xd274e283aed069cd",
    )
    assert "1s0x94b9bf3b574d7799:0xd274e283aed069cd" in u


def test_extrair_hex_ftid():
    from tools.maps_place_id import extrair_hex_ftid_de_url

    url = (
        "https://www.google.com/maps/place/x/data=!3m1!4b1!4m6!3m5!"
        "1s0x94b9bf3b574d7799:0xd274e283aed069cd!8m2!3d-21!4d-47"
    )
    assert extrair_hex_ftid_de_url(url) == "0x94b9bf3b574d7799:0xd274e283aed069cd"
