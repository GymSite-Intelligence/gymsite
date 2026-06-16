"""
Cache persistente/compartilhado de inteligência de concorrente (SearchAPI Instagram).

Resolve 2 problemas:
1. Cache de ARQUIVO (competitor_cache/) não persiste no Cloud Run → toda run re-paga.
   Aqui o cache vive no Supabase (tabela `competidor_intel_cache`), compartilhado entre
   TODOS os relatórios/bairros, keyed por place_id (ID estável do Google).
2. O JSON cru do SearchAPI é uma bomba de token (URLs, carousel_items, thumbnails). Aqui
   o pré-processamento é DETERMINÍSTICO: slim dos posts (sem ruído) + métricas computadas
   em Python. Só o resumo enxuto vai pro LLM downstream.

Freshness: `get_or_fetch_ig_intel(place_id, ttl_dias)` reusa se `collected_at` dentro do
TTL; senão chama SearchAPI 1×, computa, faz upsert. Economiza chamada (concorrentes se
repetem entre bairros). NÃO está plugado no pipeline ainda — camada isolada.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Optional

_SEARCHAPI_URL = "https://www.searchapi.io/api/v1/search"
_DEFAULT_TTL_DIAS = 14  # marketing IG muda devagar; recalibrável via param() pelo caller


# ── SearchAPI fetch ───────────────────────────────────────────────────────────
def _searchapi_key() -> str:
    return (os.getenv("SEARCHAPI_KEY") or "").strip()


def fetch_ig_searchapi(username: str, *, timeout: float = 30.0) -> Optional[dict]:
    """Chama SearchAPI engine=instagram_profile. Retorna {profile, posts} ou None."""
    key = _searchapi_key()
    if not key or not (username or "").strip():
        return None
    import httpx

    try:
        with httpx.Client(timeout=timeout) as cli:
            r = cli.get(_SEARCHAPI_URL, params={
                "engine": "instagram_profile", "username": username.strip(), "api_key": key,
            })
            r.raise_for_status()
            d = r.json()
    except Exception:
        return None
    if not isinstance(d, dict) or "profile" not in d:
        return None
    return {"profile": d.get("profile") or {}, "posts": d.get("posts") or []}


# ── Pré-processamento determinístico (sem ruído de URL) ───────────────────────
def slim_posts(posts: list) -> list[dict]:
    """Mantém só o sinal (type, likes, comments, views, date, caption); descarta
    URLs/carousel_items/thumbnails (ruído de token)."""
    out: list[dict] = []
    for p in posts or []:
        if not isinstance(p, dict):
            continue
        out.append({
            "type": p.get("type"),
            "likes": int(p.get("likes") or 0),
            "comments": int(p.get("comments") or 0),
            "views": int(p.get("views") or 0) or None,
            "date": p.get("iso_date"),
            "caption": (p.get("caption") or "")[:600],
        })
    return out


def _cadencia_posts_semana(posts_slim: list[dict]) -> float:
    datas = []
    for p in posts_slim:
        d = p.get("date")
        if d:
            try:
                datas.append(datetime.fromisoformat(str(d).replace("Z", "+00:00")))
            except Exception:
                pass
    if len(datas) < 2:
        return 0.0
    span_dias = max(1.0, (max(datas) - min(datas)).total_seconds() / 86400.0)
    return round(len(datas) / (span_dias / 7.0), 2)


def calcular_metricas(profile: dict, posts_slim: list[dict]) -> dict:
    """Métricas determinísticas de marketing IG (substrato da skill de mkt)."""
    from collections import Counter

    foll = int((profile or {}).get("followers") or 0)
    mix = Counter(p.get("type") for p in posts_slim if p.get("type"))
    engs = [(p["likes"] + p["comments"]) for p in posts_slim]
    eng_rate = round(100.0 * (sum(engs) / len(engs)) / foll, 2) if (engs and foll) else 0.0
    # engajamento médio por formato
    eng_por_formato = {}
    for t in mix:
        e = [(p["likes"] + p["comments"]) for p in posts_slim if p.get("type") == t]
        if e:
            eng_por_formato[t] = round(sum(e) / len(e))
    campeao = max(posts_slim, key=lambda p: p["likes"], default=None)
    # serviços revelados nas captions (reusa o detector da mineração)
    servicos = []
    try:
        from tools.competitor_offer_mapper import _detectar_modalidades
        servicos = _detectar_modalidades(" ".join(p.get("caption") or "" for p in posts_slim))
    except Exception:
        pass
    return {
        "followers": foll,
        "n_posts_amostra": len(posts_slim),
        "mix_formato": dict(mix),
        "eng_rate_pct": eng_rate,
        "eng_medio_por_formato": eng_por_formato,
        "cadencia_posts_semana": _cadencia_posts_semana(posts_slim),
        "post_campeao": (
            {"type": campeao["type"], "likes": campeao["likes"],
             "views": campeao.get("views"), "trecho": (campeao.get("caption") or "")[:120]}
            if campeao else None
        ),
        "servicos_detectados_ig": servicos,
    }


# ── Cache (Supabase) ──────────────────────────────────────────────────────────
def _sb():
    from tools.supabase_client import load_create_client

    url = os.environ.get("SUPABASE_URL", "").strip()
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY") or "").strip()
    if not url or not key:
        return None
    return load_create_client()(url, key)


def _cache_fresco(place_id: str, ttl_dias: int) -> Optional[dict]:
    sb = _sb()
    if not sb or not place_id:
        return None
    try:
        res = (sb.table("competidor_intel_cache").select("*")
               .eq("place_id", place_id).limit(1).execute())
        row = (res.data or [None])[0]
        if not row or not row.get("collected_at"):
            return None
        col = datetime.fromisoformat(str(row["collected_at"]).replace("Z", "+00:00"))
        idade_dias = (datetime.now(timezone.utc) - col).total_seconds() / 86400.0
        return row if idade_dias <= ttl_dias else None
    except Exception:
        return None


def _upsert_cache(reg: dict) -> None:
    sb = _sb()
    if not sb:
        return
    try:
        reg = {**reg, "collected_at": datetime.now(timezone.utc).isoformat(),
               "updated_at": datetime.now(timezone.utc).isoformat()}
        sb.table("competidor_intel_cache").upsert(reg, on_conflict="place_id").execute()
    except Exception:
        pass


def get_or_fetch_ig_intel(
    place_id: str,
    instagram_username: str,
    *,
    cidade: str = "",
    bairro: str = "",
    ttl_dias: int = _DEFAULT_TTL_DIAS,
    planos_precos: list | None = None,
) -> Optional[dict]:
    """Retorna a intel de IG do concorrente — do cache se fresco (≤ ttl_dias), senão
    busca no SearchAPI 1×, pré-processa e faz upsert. None se sem username/key/erro.

    O registro tem `_fonte` = 'cache' | 'searchapi' pra telemetria de economia."""
    if place_id:
        cached = _cache_fresco(place_id, ttl_dias)
        if cached:
            return {**cached, "_fonte": "cache"}

    raw = fetch_ig_searchapi(instagram_username)
    if not raw:
        return None
    profile = raw["profile"]
    posts_slim = slim_posts(raw["posts"])
    metricas = calcular_metricas(profile, posts_slim)
    reg = {
        "place_id": place_id,
        "instagram_username": instagram_username,
        "cidade": cidade, "bairro": bairro,
        "profile": {
            "username": profile.get("username"), "name": profile.get("name"),
            "bio": profile.get("bio"), "followers": profile.get("followers"),
            "following": profile.get("following"), "posts": profile.get("posts"),
            "is_business": profile.get("is_business"),
            "external_link": profile.get("external_link"),
        },
        "posts_slim": posts_slim,
        "metricas": metricas,
        "planos_precos": planos_precos,
        "servicos": metricas.get("servicos_detectados_ig"),
    }
    _upsert_cache(reg)
    return {**reg, "_fonte": "searchapi"}
