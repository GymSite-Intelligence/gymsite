"""Pré-processamento determinístico do cache de inteligência de concorrente
(slim de posts + métricas de marketing IG). Partes puras — sem rede/Supabase."""
from tools.competidor_intel_cache import calcular_metricas, slim_posts


_RAW_POSTS = [
    {"type": "carousel", "likes": 848, "comments": 76, "iso_date": "2026-06-10T15:04:02Z",
     "caption": "musculação cardio nutricionista", "link": "https://noise...", "thumbnail": "https://x"},
    {"type": "reel", "likes": 9512, "comments": 358, "views": 102581, "iso_date": "2026-03-21T15:02:07Z",
     "caption": "cross cardio nutricionista coworking", "carousel_items": [{"link": "https://noise"}]},
    {"type": "reel", "likes": 284, "comments": 19, "views": 3800, "iso_date": "2026-06-04T15:00:11Z",
     "caption": "moovz cross"},
]


def test_slim_remove_ruido_de_url():
    s = slim_posts(_RAW_POSTS)
    assert len(s) == 3
    p0 = s[0]
    # mantém o sinal
    assert set(p0.keys()) == {"type", "likes", "comments", "views", "date", "caption"}
    # descarta o ruído
    assert "link" not in p0 and "thumbnail" not in p0 and "carousel_items" not in p0
    assert p0["likes"] == 848 and p0["type"] == "carousel"


def test_metricas_marketing():
    s = slim_posts(_RAW_POSTS)
    m = calcular_metricas({"followers": 94577}, s)
    assert m["mix_formato"] == {"carousel": 1, "reel": 2}
    assert m["followers"] == 94577
    assert m["eng_rate_pct"] > 0
    assert m["post_campeao"]["likes"] == 9512  # o reel viral
    assert m["post_campeao"]["type"] == "reel"
    # serviços detectados nas captions (alimenta a ERRC)
    assert "nutricao" in m["servicos_detectados_ig"]


def test_metricas_sem_posts_nao_quebra():
    m = calcular_metricas({"followers": 0}, [])
    assert m["mix_formato"] == {}
    assert m["eng_rate_pct"] == 0.0
    assert m["post_campeao"] is None
