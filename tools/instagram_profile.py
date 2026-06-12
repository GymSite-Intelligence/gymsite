"""Instagram Profile via SearchAPI.io (engine=instagram_profile).

Dados públicos de perfil: nome, bio, seguidores, posts, links. Uso no
GymSite: atividade de marketing REAL dos concorrentes (followers + bio +
link) sem o Playwright frágil do A3c (que derrubava o processo — run
9213f40d). Plano pago SearchAPI ativo desde 12/06.

Auth preferencial: header `Authorization: Bearer` (spec da engine);
fallback impossível de errar porque a key nunca vai em código.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any

import requests

logger = logging.getLogger("gymsite.instagram")

_SEARCHAPI_URL = "https://www.searchapi.io/api/v1/search"

# instagram.com/<user>/ — ignora paths reservados que não são perfis.
_IG_URL_RE = re.compile(
    r"instagram\.com/([A-Za-z0-9_.]{2,30})/?",
    re.IGNORECASE,
)
_IG_RESERVED = {"p", "reel", "reels", "stories", "explore", "accounts", "tv", "direct"}


def extrair_username_instagram(url_ou_texto: str | None) -> str | None:
    """Extrai username de uma URL/texto contendo instagram.com/<user>."""
    if not url_ou_texto:
        return None
    m = _IG_URL_RE.search(url_ou_texto)
    if not m:
        return None
    user = m.group(1).strip(".").lower()
    if user in _IG_RESERVED or len(user) < 2:
        return None
    return user


def descobrir_instagram_no_site(url: str | None, timeout: int = 12) -> str | None:
    """Acha o @ do Instagram no HTML do site OFICIAL do concorrente.

    Site próprio e IG são complementares (decisão 12/06): quando o website
    não É instagram.com, o link do IG costuma estar no rodapé/header do
    site. Match continua 100% auditável — veio do site oficial, não de
    chute por nome. Lê no máximo ~300KB; falha → None.
    """
    url = (url or "").strip()
    if not url or "instagram.com" in url.lower():
        return None
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    try:
        r = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (compatible; GymSiteBot/1.0)"},
            stream=True,
        )
        r.raise_for_status()
        html = next(r.iter_content(chunk_size=300_000)).decode("utf-8", errors="ignore")
    except Exception as e:
        logger.debug("descobrir_instagram_no_site %s: %s", url[:60], type(e).__name__)
        return None
    for m in _IG_URL_RE.finditer(html):
        user = m.group(1).strip(".").lower()
        if user not in _IG_RESERVED and len(user) >= 2:
            return user
    return None


def _name_tokens(nome: str) -> set[str]:
    nome = re.sub(r"[^\w\s]", " ", (nome or "").lower())
    return {t for t in nome.split() if len(t) >= 3}


def _nome_bate(nome_perfil: str | None, nome_socio: str) -> bool:
    """Match conservador: ≥2 tokens do nome do sócio no nome do perfil
    (ou 1 token quando o nome do sócio só tem 1 token útil)."""
    p, s = _name_tokens(nome_perfil or ""), _name_tokens(nome_socio)
    if not p or not s:
        return False
    overlap = len(p & s)
    return overlap >= 2 or (overlap == 1 and len(s) == 1)


def descobrir_instagram_do_socio(
    nome_socio: str,
    nome_academia: str,
    ig_academia: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """IG do sócio administrador (QSA) — descoberta em camadas auditáveis.

    Camada 1 (confiança ALTA): @ mencionado na bio / bio_links do IG da
    academia ("por @fulanopersonal" é padrão de dono de academia pequena).
    Camada 2 (confiança MÉDIA): busca Google (SearchAPI engine=google) por
    "<nome socio>" <academia> instagram → candidatos instagram.com/<user>
    → aceita SÓ se o nome do perfil bater com o do sócio (≥2 tokens).
    Sem match validado → None. NUNCA chuta username por slug do nome —
    homônimo no relatório é pior que campo vazio (P-004).
    """
    key = (os.getenv("SEARCHAPI_KEY") or "").strip()
    nome_socio = (nome_socio or "").strip()
    if not nome_socio or len(nome_socio) < 5:
        return None

    # Camada 1 — bio/links do IG da academia
    if isinstance(ig_academia, dict):
        textos = [ig_academia.get("bio") or ""]
        for bl in ig_academia.get("bio_links") or []:
            if isinstance(bl, dict):
                textos.append(str(bl.get("link") or bl.get("url") or ""))
            else:
                textos.append(str(bl))
        textos.append(str(ig_academia.get("external_link") or ""))
        candidatos: list[str] = []
        for t in textos:
            candidatos += [u.lower().strip(".") for u in re.findall(r"@([A-Za-z0-9_.]{2,30})", t)]
            u2 = extrair_username_instagram(t)
            if u2:
                candidatos.append(u2)
        proprio = (ig_academia.get("username") or "").lower()
        for cand in candidatos:
            if cand in _IG_RESERVED or cand == proprio:
                continue
            perfil = get_instagram_profile(cand)
            if perfil and _nome_bate(perfil.get("name"), nome_socio):
                perfil["confianca"] = "alta"
                perfil["fonte_descoberta"] = "bio do IG da academia"
                return perfil

    # Camada 2 — Google search via SearchAPI + validação de nome
    if not key:
        return None
    try:
        r = requests.get(
            _SEARCHAPI_URL,
            headers={"Authorization": f"Bearer {key}"},
            params={
                "engine": "google",
                "q": f'"{nome_socio}" {nome_academia} instagram',
                "gl": "br",
                "hl": "pt-br",
                "num": 10,
            },
            timeout=30,
        )
        r.raise_for_status()
        organicos = r.json().get("organic_results") or []
    except Exception as e:
        logger.warning("busca IG sócio '%s' falhou: %s", nome_socio[:30], type(e).__name__)
        return None

    vistos: set[str] = set()
    for res in organicos[:8]:
        link = str(res.get("link") or "")
        user = extrair_username_instagram(link)
        if not user or user in vistos:
            continue
        vistos.add(user)
        perfil = get_instagram_profile(user)
        if perfil and _nome_bate(perfil.get("name"), nome_socio):
            perfil["confianca"] = "media"
            perfil["fonte_descoberta"] = "busca Google (nome validado no perfil)"
            return perfil
        if len(vistos) >= 3:  # no máximo 3 perfis verificados por sócio
            break
    return None


def get_instagram_profile(username: str, timeout: int = 30) -> dict[str, Any] | None:
    """Perfil público do Instagram via SearchAPI.

    Retorna dict com username, name, bio, followers, following, posts,
    is_verified, external_link, avatar — ou None (sem key, perfil
    inexistente, rate limit). Nunca lança: enriquecimento é best-effort.
    """
    key = (os.getenv("SEARCHAPI_KEY") or "").strip()
    username = (username or "").strip().lstrip("@").lower()
    if not key or not username:
        return None
    try:
        r = requests.get(
            _SEARCHAPI_URL,
            headers={"Authorization": f"Bearer {key}"},
            params={"engine": "instagram_profile", "username": username},
            timeout=timeout,
        )
        if r.status_code == 429:
            logger.warning("instagram_profile rate-limited (@%s)", username)
            return None
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning("instagram_profile @%s falhou: %s", username, type(e).__name__)
        return None

    profile = data.get("profile")
    if not isinstance(profile, dict) or not profile.get("username"):
        return None
    return {
        "username": profile.get("username"),
        "name": profile.get("name"),
        "bio": (profile.get("bio") or "")[:300] or None,
        "avatar": profile.get("avatar"),
        "is_verified": bool(profile.get("is_verified")),
        "followers": profile.get("followers"),
        "following": profile.get("following"),
        "posts": profile.get("posts"),
        "external_link": profile.get("external_link"),
        "bio_links": (profile.get("bio_links") or [])[:3],
        "fonte": "SearchAPI instagram_profile",
    }
