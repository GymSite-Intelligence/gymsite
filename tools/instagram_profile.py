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
