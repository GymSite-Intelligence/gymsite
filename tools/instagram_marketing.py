"""Instagram marketing intel — descoberta de @, posts e diagnóstico determinístico.

Reusa SearchAPI instagram_profile (posts reais) e google_light para candidatos
de academia em obra/pré-abertura. Números derivados do JSON — sem LLM.
"""
from __future__ import annotations

import logging
import os
import re
from collections import Counter, defaultdict
from typing import Any, Optional

import requests

from tools.competidor_intel_cache import (
    calcular_metricas,
    fetch_ig_searchapi,
    get_or_fetch_ig_intel,
    slim_posts,
)
from tools.instagram_profile import (
    descobrir_instagram_no_site,
    extrair_username_instagram,
)

logger = logging.getLogger("gymsite.instagram_marketing")

_SEARCHAPI_URL = "https://www.searchapi.io/api/v1/search"

_TEMA_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("diario_obra", re.compile(
        r"obra|constru|reforma|andamento|evolu[cç][aã]o|cronograma|gesso|alvenaria|"
        r"estrutura|instala[cç][aã]o|pintura|acabamento",
        re.I,
    )),
    ("pre_venda", re.compile(
        r"pr[eé][\s-]?venda|lista\s+(de\s+)?espera|lista\s+vip|reserva|garanta|"
        r"matricule|antecipe|pr[eé]\s*lan[cç]amento",
        re.I,
    )),
    ("nova_unidade", re.compile(
        r"nova\s+unidade|nova\s+filial|segunda\s+unidade|nova\s+sede|em\s+breve|"
        r"coming\s+soon|brevemente|chegando|estamos\s+chegando",
        re.I,
    )),
    ("inauguracao", re.compile(
        r"inaugura|abertura|estamos\s+abertos|grande\s+abertura|soft\s+open|opening",
        re.I,
    )),
    ("promocao", re.compile(
        r"promo[cç][aã]o|desconto|%+\s*off|black\s+friday|mensalidade|gr[aá]tis|isent",
        re.I,
    )),
    ("aluno_destaque", re.compile(
        r"transforma[cç][aã]o|antes\s+e\s+depois|resultado|alun[oa]|depoimento|jornada",
        re.I,
    )),
    ("treino_dica", re.compile(
        r"\bdica\b|workout|treino|exerc[ií]cio|s[eé]rie|muscula[cç][aã]o|hiit|funcional",
        re.I,
    )),
    ("equipe", re.compile(
        r"professor|treinador|personal|equipe|staff|time|coach",
        re.I,
    )),
    ("evento", re.compile(
        r"evento|desafio|competi[cç][aã]o|aul[aã]o|workshop|palestra",
        re.I,
    )),
]


def _searchapi_key() -> str:
    return (os.getenv("SEARCHAPI_KEY") or "").strip()


def classificar_temas_post(caption: str) -> list[str]:
    """Classifica caption em temas de marketing (multi-label)."""
    text = (caption or "").strip()
    if not text:
        return ["outro"]
    temas = [nome for nome, rx in _TEMA_RULES if rx.search(text)]
    return temas or ["outro"]


def _engagement_post(post: dict, followers: int) -> dict:
    likes = int(post.get("likes") or 0)
    comments = int(post.get("comments") or 0)
    views = int(post.get("views") or 0) or None
    eng_abs = likes + comments
    eng_rate = round(100.0 * eng_abs / followers, 3) if followers else None
    return {
        "eng_abs": eng_abs,
        "eng_rate_pct": eng_rate,
        "likes": likes,
        "comments": comments,
        "views": views,
    }


def diagnosticar_posts(
    profile: dict,
    posts_slim: list[dict],
    *,
    metricas: dict | None = None,
) -> dict:
    """Diagnóstico determinístico: temas, formato campeão, posts top."""
    followers = int((profile or {}).get("followers") or 0)
    metricas = metricas or calcular_metricas(profile, posts_slim)

    por_tema: dict[str, list[int]] = defaultdict(list)
    por_tema_formato: dict[str, Counter] = defaultdict(Counter)
    posts_diag: list[dict] = []

    for p in posts_slim:
        cap = p.get("caption") or ""
        temas = classificar_temas_post(cap)
        eng = _engagement_post(p, followers)
        for t in temas:
            por_tema[t].append(eng["eng_abs"])
            por_tema_formato[t][p.get("type") or "desconhecido"] += 1
        posts_diag.append({
            "date": p.get("date"),
            "type": p.get("type"),
            "temas": temas,
            "trecho_caption": cap[:160],
            **eng,
        })

    posts_diag.sort(key=lambda x: x["eng_abs"], reverse=True)

    tema_eng_medio = {
        t: round(sum(v) / len(v)) for t, v in por_tema.items() if v
    }
    tema_campeao = (
        max(tema_eng_medio.items(), key=lambda kv: kv[1])[0]
        if tema_eng_medio else None
    )

    mix = metricas.get("mix_formato") or {}
    formato_campeao = (
        max(
            (metricas.get("eng_medio_por_formato") or {}).items(),
            key=lambda kv: kv[1],
        )[0]
        if metricas.get("eng_medio_por_formato") else None
    )

    temas_obra = {"diario_obra", "pre_venda", "nova_unidade", "inauguracao"}
    posts_obra = [p for p in posts_diag if temas_obra & set(p["temas"])]

    return {
        "metricas": metricas,
        "formato_campeao_engajamento": formato_campeao,
        "tema_campeao_engajamento": tema_campeao,
        "eng_medio_por_tema": tema_eng_medio,
        "mix_formato_por_tema": {k: dict(v) for k, v in por_tema_formato.items()},
        "top_posts": posts_diag[:5],
        "posts_pre_abertura_obra": posts_obra[:8],
        "tem_metodologia_obra": bool(posts_obra),
    }


def _name_tokens(nome: str) -> set[str]:
    nome = re.sub(r"[^\w\s]", " ", (nome or "").lower())
    return {t for t in nome.split() if len(t) >= 3}


def _perfil_bate_academia(nome_perfil: str | None, nome_academia: str) -> bool:
    p, a = _name_tokens(nome_perfil or ""), _name_tokens(nome_academia)
    if not p or not a:
        return False
    overlap = len(p & a)
    return overlap >= 2 or (overlap == 1 and len(a) == 1)


def descobrir_instagram_por_nome(
    nome_academia: str,
    *,
    bairro: str = "",
    cidade: str = "",
) -> tuple[str | None, str]:
    """Busca Google (google_light) por perfil IG da academia. Retorna (username, fonte)."""
    key = _searchapi_key()
    nome = (nome_academia or "").strip()
    if not key or not nome:
        return None, "indisponivel"

    q = " ".join(p for p in (nome, "instagram", bairro, cidade) if p)
    try:
        r = requests.get(
            _SEARCHAPI_URL,
            headers={"Authorization": f"Bearer {key}"},
            params={"engine": "google_light", "q": q, "gl": "br", "hl": "pt-br"},
            timeout=25,
        )
        r.raise_for_status()
        organicos = r.json().get("organic_results") or []
    except Exception as exc:
        logger.debug("google_light IG nome '%s': %s", nome[:40], type(exc).__name__)
        return None, "google_light_erro"

    vistos: set[str] = set()
    for res in organicos[:10]:
        if not isinstance(res, dict):
            continue
        for field in ("link", "displayed_link"):
            user = extrair_username_instagram(str(res.get(field) or ""))
            if not user or user in vistos:
                continue
            vistos.add(user)
            raw = fetch_ig_searchapi(user)
            if raw and _perfil_bate_academia((raw.get("profile") or {}).get("name"), nome):
                return user, "google_light (nome validado no perfil)"
            if len(vistos) >= 4:
                break
        if vistos and len(vistos) >= 4:
            break

    for res in organicos[:6]:
        user = extrair_username_instagram(str((res or {}).get("link") or ""))
        if user and user not in vistos:
            return user, "google_light (link instagram, sem validação de nome)"
    return None, "google_light_sem_match"


def resolver_instagram_concorrente(
    *,
    nome: str,
    website: str = "",
    place_id: str = "",
    bairro: str = "",
    cidade: str = "",
) -> dict:
    """Cascata auditável: website→IG, HTML do site, Place Details, Google por nome."""
    site = (website or "").strip()
    fonte = ""
    username = extrair_username_instagram(site) if site else None
    if username:
        fonte = "website já é instagram.com"

    if not username and site:
        username = descobrir_instagram_no_site(site)
        if username:
            fonte = "link no HTML do site oficial"

    if not username and place_id:
        try:
            from tools.maps_tools import obter_detalhes_contato

            det = obter_detalhes_contato(place_id)
            if isinstance(det, dict) and det.get("website"):
                site2 = det["website"]
                username = extrair_username_instagram(site2) or descobrir_instagram_no_site(site2)
                if username:
                    site = site2
                    fonte = "Place Details → site oficial"
        except Exception:
            pass

    if not username and nome:
        username, fonte_g = descobrir_instagram_por_nome(
            nome, bairro=bairro, cidade=cidade,
        )
        if username:
            fonte = fonte_g

    return {
        "username": username,
        "website": site or None,
        "fonte_descoberta": fonte or None,
        "place_id": place_id or None,
        "nome": nome,
    }


def fetch_intel_com_posts(
    place_id: str,
    username: str,
    *,
    cidade: str = "",
    bairro: str = "",
    usar_cache: bool = True,
) -> Optional[dict]:
    """Perfil + posts slim + métricas + diagnóstico."""
    raw_intel: Optional[dict] = None
    if usar_cache and place_id:
        raw_intel = get_or_fetch_ig_intel(
            place_id, username, cidade=cidade, bairro=bairro, ttl_dias=14,
        )
    if not raw_intel:
        raw = fetch_ig_searchapi(username)
        if not raw:
            return None
        profile = raw["profile"]
        posts_slim = slim_posts(raw["posts"])
        metricas = calcular_metricas(profile, posts_slim)
        raw_intel = {
            "profile": profile,
            "posts_slim": posts_slim,
            "metricas": metricas,
            "_fonte": "searchapi",
        }

    profile = raw_intel.get("profile") or {}
    posts_slim = raw_intel.get("posts_slim") or []
    diag = diagnosticar_posts(profile, posts_slim, metricas=raw_intel.get("metricas"))
    return {
        **raw_intel,
        "diagnostico": diag,
        "instagram_username": username,
    }


_OBRA_QUERIES = (
    'site:instagram.com academia "em breve" {bairro} {cidade}',
    'site:instagram.com academia obra {bairro} {cidade}',
    'site:instagram.com academia "pré-venda" {bairro} {cidade}',
    'site:instagram.com academia inauguração {bairro} {cidade}',
    'site:instagram.com "diário de obra" academia {cidade}',
)


def _google_light_organic(q: str) -> list[dict]:
    key = _searchapi_key()
    if not key:
        return []
    try:
        from tools.search_raw_cache import get_search_raw, set_search_raw

        params = {"engine": "google_light", "q": q, "gl": "br", "hl": "pt-br"}
        cached = get_search_raw("google_light", params)
        if cached:
            return cached.get("organic_results") or []

        r = requests.get(
            _SEARCHAPI_URL,
            headers={"Authorization": f"Bearer {key}"},
            params=params,
            timeout=25,
        )
        r.raise_for_status()
        data = r.json()
        try:
            set_search_raw("google_light", params, data)
        except Exception:
            pass
        return data.get("organic_results") or []
    except Exception as exc:
        logger.debug("google_light obra: %s", type(exc).__name__)
        return []


def buscar_candidatos_ig_obra(
    *,
    cidade: str,
    bairro: str = "",
    uf: str = "",
    max_perfis: int = 5,
) -> dict:
    """Busca independente de perfis IG com sinais de obra/pré-abertura na praça."""
    loc = " ".join(p for p in (bairro, cidade, uf) if p).strip()
    candidatos: dict[str, dict] = {}

    for tpl in _OBRA_QUERIES:
        q = tpl.format(bairro=bairro or cidade, cidade=cidade)
        for res in _google_light_organic(q):
            if not isinstance(res, dict):
                continue
            link = str(res.get("link") or "")
            user = extrair_username_instagram(link)
            if not user or user in candidatos:
                continue
            snippet = (res.get("snippet") or "")[:300]
            title = (res.get("title") or "")[:200]
            candidatos[user] = {
                "username": user,
                "titulo_busca": title,
                "snippet": snippet,
                "link": link,
                "query_origem": q,
            }
            if len(candidatos) >= max_perfis * 2:
                break

    perfis: list[dict] = []
    for user, meta in list(candidatos.items())[:max_perfis]:
        intel = fetch_intel_com_posts("", user, usar_cache=False)
        if not intel:
            perfis.append({**meta, "status": "perfil_indisponivel"})
            continue
        diag = intel.get("diagnostico") or {}
        perfis.append({
            **meta,
            "status": "ok",
            "followers": (intel.get("profile") or {}).get("followers"),
            "n_posts_amostra": len(intel.get("posts_slim") or []),
            "tem_metodologia_obra": diag.get("tem_metodologia_obra"),
            "tema_campeao": diag.get("tema_campeao_engajamento"),
            "formato_campeao": diag.get("formato_campeao_engajamento"),
            "posts_pre_abertura_obra": diag.get("posts_pre_abertura_obra") or [],
            "metricas": diag.get("metricas"),
            "top_posts": diag.get("top_posts") or [],
        })

    return {
        "status": "ok" if perfis else "indisponivel",
        "cidade": cidade,
        "bairro": bairro or None,
        "uf": uf or None,
        "queries": [t.format(bairro=bairro or cidade, cidade=cidade) for t in _OBRA_QUERIES],
        "candidatos_links": len(candidatos),
        "perfis": perfis,
        "carimbo": (
            f"{len(perfis)} perfis IG obra · {len(candidatos)} links · "
            f"google_light+instagram_profile · {loc}"
        ),
    }


def analisar_concorrentes_com_reviews(
    *,
    cidade: str,
    uf: str,
    bairro: str,
    tipo_negocio: str = "academia",
    max_concorrentes: int = 5,
) -> dict:
    """Gate reviews do bairro → descobre @ de cada um → posts + diagnóstico."""
    from tools.competitor_tools import buscar_reviews_academia, cross_check_concorrentes_bairro

    mercado = cross_check_concorrentes_bairro(cidade, uf, bairro, tipo_negocio)
    if mercado.get("status") == "indisponivel":
        return {
            "status": "indisponivel",
            "concorrentes_com_reviews": 0,
            "perfis_ig": [],
            "carimbo": "0 IG · mercado indisponível",
        }

    com_reviews: list[dict] = []
    for c in (mercado.get("no_bairro") or [])[:max(1, min(max_concorrentes, 20))]:
        if not isinstance(c, dict):
            continue
        pid = (c.get("place_id") or "").strip()
        if not pid:
            continue
        rev = buscar_reviews_academia(pid, c.get("nome") or "")
        if not rev.get("reviews"):
            continue
        com_reviews.append({
            "place_id": pid,
            "nome": c.get("nome") or rev.get("nome") or "",
            "rating_geral": rev.get("rating_geral") or c.get("rating"),
            "num_avaliacoes": rev.get("total_avaliacoes") or c.get("num_avaliacoes"),
        })

    perfis_ig: list[dict] = []
    for c in com_reviews:
        desc = resolver_instagram_concorrente(
            nome=c["nome"],
            place_id=c["place_id"],
            bairro=bairro,
            cidade=cidade,
        )
        username = desc.get("username")
        item: dict[str, Any] = {
            "place_id": c["place_id"],
            "nome": c["nome"],
            "rating_geral": c.get("rating_geral"),
            "num_avaliacoes": c.get("num_avaliacoes"),
            "descoberta": desc,
        }
        if not username:
            item["status"] = "ig_nao_encontrado"
            perfis_ig.append(item)
            continue

        intel = fetch_intel_com_posts(
            c["place_id"], username, cidade=cidade, bairro=bairro,
        )
        if not intel:
            item["status"] = "perfil_indisponivel"
            item["username"] = username
            perfis_ig.append(item)
            continue

        diag = intel.get("diagnostico") or {}
        item.update({
            "status": "ok",
            "username": username,
            "followers": (intel.get("profile") or {}).get("followers"),
            "metricas": diag.get("metricas"),
            "diagnostico": {
                "formato_campeao_engajamento": diag.get("formato_campeao_engajamento"),
                "tema_campeao_engajamento": diag.get("tema_campeao_engajamento"),
                "eng_medio_por_tema": diag.get("eng_medio_por_tema"),
                "mix_formato_por_tema": diag.get("mix_formato_por_tema"),
                "tem_metodologia_obra": diag.get("tem_metodologia_obra"),
                "top_posts": diag.get("top_posts"),
                "posts_pre_abertura_obra": diag.get("posts_pre_abertura_obra"),
            },
            "_fonte_ig": intel.get("_fonte"),
        })
        perfis_ig.append(item)

    ok_n = sum(1 for p in perfis_ig if p.get("status") == "ok")
    return {
        "status": "ok",
        "query": mercado.get("query"),
        "gated_n": mercado.get("gated_n"),
        "concorrentes_com_reviews": len(com_reviews),
        "perfis_ig_ok": ok_n,
        "perfis_ig": perfis_ig,
        "carimbo": (
            f"{ok_n}/{len(com_reviews)} IG c/ posts · {len(com_reviews)} c/ reviews · "
            f"SearchAPI instagram_profile · gate {bairro}/{cidade}-{uf}"
        ),
    }
