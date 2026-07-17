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
    dados = {"status": "sem_popular_times", "fonte": "playwright_maps_dom"}
    assert _cache_deve_ignorar(
        dados, force_refresh=False, nome="Smart Fit Neo", lat=-21.1, lng=-47.8
    )
    assert not _cache_deve_ignorar(
        dados, force_refresh=False, nome="", lat=-21.1, lng=-47.8
    )


def test_cache_respeita_sem_pico_searchapi():
    dados = {"status": "sem_popular_times", "fonte": "searchapi"}
    assert not _cache_deve_ignorar(
        dados, force_refresh=False, nome="Smart Fit", lat=-3.7, lng=-38.5
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


def test_place_raw_evita_playwright(monkeypatch):
    import asyncio
    from tools import popular_times_tool as pt

    calls = {"pw": 0, "net": 0}

    monkeypatch.setattr(pt, "_load_pico_cache", lambda *a, **k: None)
    monkeypatch.setattr(pt, "_save_pico_cache", lambda *a, **k: None)
    monkeypatch.setattr(
        pt,
        "_tentar_searchapi",
        lambda *a, **k: calls.__setitem__("net", calls["net"] + 1) or None,
    )

    def boom(*a, **k):
        calls["pw"] += 1
        raise AssertionError("Playwright não deve rodar")

    monkeypatch.setattr(pt, "_extrair_sync", boom)

    raw = {
        "place_result": {
            "popular_times": {
                "chart": {
                    "monday": [
                        {"time": "18:00", "busyness_score": 90},
                        {"time": "10:00", "busyness_score": 40},
                    ]
                }
            }
        }
    }
    out = asyncio.run(
        pt.pesquisar_horarios_pico(
            "https://maps.google.com/?q=place_id:ChIJx",
            "ChIJx",
            nome="X",
            lat=-3.7,
            lng=-38.5,
            place_raw=raw,
        )
    )
    assert out["status"] == "ok"
    assert out["fonte"] == "searchapi"
    assert out["dados_por_dia"]["segunda"]["18"] == 90
    assert calls["pw"] == 0
    assert calls["net"] == 0


def test_searchapi_sem_pico_nao_cai_em_playwright(monkeypatch):
    import asyncio
    from tools import popular_times_tool as pt

    monkeypatch.setattr(pt, "_load_pico_cache", lambda *a, **k: None)
    saved = {}
    monkeypatch.setattr(pt, "_save_pico_cache", lambda pid, r: saved.update(r))
    monkeypatch.setattr(
        pt,
        "_tentar_searchapi",
        lambda pid: {
            "status": "sem_popular_times",
            "place_id": pid,
            "dados_por_dia": {},
            "fonte": "searchapi",
        },
    )
    monkeypatch.setattr(
        pt,
        "_extrair_sync",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no PW")),
    )

    out = asyncio.run(
        pt.pesquisar_horarios_pico(
            "https://maps.google.com/?q=place_id:ChIJy",
            "ChIJy",
            nome="Y",
            lat=-3.7,
            lng=-38.5,
        )
    )
    assert out["status"] == "sem_popular_times"
    assert out["fonte"] == "searchapi"
    assert saved.get("fonte") == "searchapi"
