"""MCP segmento Social — Instagram via SearchAPI instagram_profile."""

from __future__ import annotations

from typing import Any

SOCIAL_TOOLS: list[dict[str, Any]] = [
    {
        "name": "gymsite_social_instagram_profile",
        "description": (
            "Perfil público Instagram (username) via SearchAPI instagram_profile. "
            "Retorna followers, posts, bio, links — sinal de marketing real."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "Com ou sem @"},
            },
            "required": ["username"],
        },
    },
    {
        "name": "gymsite_social_instagram_from_site",
        "description": (
            "Descobre @ Instagram no HTML do site oficial do concorrente e, se achar, "
            "busca perfil via SearchAPI."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "website_url": {"type": "string"},
                "fetch_profile": {"type": "boolean", "default": True},
            },
            "required": ["website_url"],
        },
    },
    {
        "name": "gymsite_social_instagram_concorrentes_reviews",
        "description": (
            "TESTE: para concorrentes do bairro COM reviews, descobre @ (site/Place Details/"
            "Google), busca posts via SearchAPI instagram_profile e retorna diagnóstico "
            "determinístico (formato/tema que engaja, posts obra/pré-venda)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "cidade": {"type": "string"},
                "uf": {"type": "string"},
                "bairro": {"type": "string"},
                "tipo_negocio": {
                    "type": "string",
                    "default": "academia",
                },
                "max_concorrentes": {
                    "type": "integer",
                    "default": 5,
                    "description": "Teto de concorrentes com reviews a analisar (custo API)",
                },
            },
            "required": ["cidade", "uf", "bairro"],
        },
    },
    {
        "name": "gymsite_social_instagram_obra_busca",
        "description": (
            "TESTE: busca independente de perfis IG com sinais de obra/pré-abertura/inauguração "
            "na praça (google_light site:instagram.com), depois posts + diagnóstico de engajamento."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "cidade": {"type": "string"},
                "uf": {"type": "string"},
                "bairro": {"type": "string"},
                "max_perfis": {
                    "type": "integer",
                    "default": 5,
                    "description": "Máximo de perfis IG a buscar (custo API)",
                },
            },
            "required": ["cidade", "uf"],
        },
    },
]


def _slim_ig(profile: dict) -> dict:
    return {
        "username": profile.get("username"),
        "name": profile.get("name"),
        "bio": profile.get("bio"),
        "followers": profile.get("followers"),
        "following": profile.get("following"),
        "posts": profile.get("posts"),
        "is_verified": profile.get("is_verified"),
        "external_link": profile.get("external_link"),
        "bio_links": profile.get("bio_links"),
        "fonte": profile.get("fonte"),
        "confianca": profile.get("confianca"),
        "fonte_descoberta": profile.get("fonte_descoberta"),
    }


async def handle_instagram_profile(args: dict) -> dict:
    from tools.instagram_profile import get_instagram_profile

    username = (args.get("username") or "").strip().lstrip("@")
    if not username:
        return {"status": "erro", "detail": "username vazio"}

    profile = get_instagram_profile(username)
    if not profile:
        return {
            "status": "indisponivel",
            "username": username,
            "carimbo": f"perfil @{username} · SearchAPI instagram_profile · indisponível",
        }

    slim = _slim_ig(profile)
    followers = profile.get("followers")
    posts = profile.get("posts")
    slim["status"] = "ok"
    slim["carimbo"] = (
        f"@{username} · {followers or '?'} seguidores · {posts or '?'} posts · "
        f"SearchAPI instagram_profile"
    )
    return slim


async def handle_instagram_from_site(args: dict) -> dict:
    from tools.instagram_profile import descobrir_instagram_no_site, get_instagram_profile

    url = (args.get("website_url") or "").strip()
    fetch_profile = args.get("fetch_profile", True)
    if not url:
        return {"status": "erro", "detail": "website_url vazio"}

    username = descobrir_instagram_no_site(url)
    if not username:
        return {
            "status": "indisponivel",
            "website_url": url,
            "carimbo": f"site {url[:60]} · IG não encontrado no HTML",
        }

    out: dict[str, Any] = {
        "status": "ok",
        "website_url": url,
        "username": username,
        "fonte_descoberta": "site oficial (HTML)",
    }
    if fetch_profile:
        profile = get_instagram_profile(username)
        if profile:
            out["perfil"] = _slim_ig(profile)
            out["carimbo"] = (
                f"@{username} · site oficial · "
                f"{profile.get('followers') or '?'} seguidores · SearchAPI instagram_profile"
            )
        else:
            out["status"] = "parcial"
            out["carimbo"] = f"@{username} · site oficial · perfil SearchAPI indisponível"
    else:
        out["carimbo"] = f"@{username} · descoberto no site oficial"
    return out


async def handle_instagram_concorrentes_reviews(args: dict) -> dict:
    from tools.instagram_marketing import analisar_concorrentes_com_reviews

    return analisar_concorrentes_com_reviews(
        cidade=args["cidade"],
        uf=args["uf"],
        bairro=args["bairro"],
        tipo_negocio=args.get("tipo_negocio") or "academia",
        max_concorrentes=int(args.get("max_concorrentes") or 5),
    )


async def handle_instagram_obra_busca(args: dict) -> dict:
    from tools.instagram_marketing import buscar_candidatos_ig_obra

    return buscar_candidatos_ig_obra(
        cidade=args["cidade"],
        uf=args.get("uf") or "",
        bairro=args.get("bairro") or "",
        max_perfis=max(1, min(int(args.get("max_perfis") or 5), 8)),
    )


SOCIAL_HANDLERS = {
    "gymsite_social_instagram_profile": handle_instagram_profile,
    "gymsite_social_instagram_from_site": handle_instagram_from_site,
    "gymsite_social_instagram_concorrentes_reviews": handle_instagram_concorrentes_reviews,
    "gymsite_social_instagram_obra_busca": handle_instagram_obra_busca,
}
