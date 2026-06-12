# -*- coding: utf-8 -*-
"""Backfill instagram_profile em competidores cujo website é instagram.com/<user>.

Uso: python scripts/backfill_instagram.py <relatorio_id> [...]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv(override=True)

from supabase import create_client

from tools.instagram_profile import (
    descobrir_instagram_no_site,
    extrair_username_instagram,
    get_instagram_profile,
)

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

for rid in sys.argv[1:]:
    rows = (
        sb.table("competidores")
        .select("id, nome, website, instagram_profile")
        .eq("relatorio_id", rid)
        .execute()
    ).data or []
    print(f"[{rid[:8]}] {len(rows)} competidores")
    for c in rows:
        if c.get("instagram_profile"):
            continue
        site = c.get("website") or ""
        user = extrair_username_instagram(site)
        if not user and site:
            user = descobrir_instagram_no_site(site)
        if not user:
            print(f"  - {c['nome']}: IG nao descoberto (site: {site[:40] or 'nenhum'})")
            continue
        p = get_instagram_profile(user)
        if not p:
            print(f"  - {c['nome']}: @{user} sem perfil/falha")
            continue
        sb.table("competidores").update({"instagram_profile": p}).eq("id", c["id"]).execute()
        print(f"  + {c['nome']}: @{p['username']} | {p.get('followers')} seguidores | {p.get('posts')} posts")
