import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

GRAPH = "https://graph.facebook.com/v21.0"
TOKEN = (os.getenv("IG_GRAPH_TOKEN") or "").strip()
IG_ID = (os.getenv("IG_BUSINESS_ID") or "").strip()
SAIDA = RAIZ / "docs" / "produto" / "brand" / "instagram" / "reports"


def falha(msg):
    print(f"[ig-report] {msg}")
    sys.exit(1)


def gget(path, **params):
    params["access_token"] = TOKEN
    r = requests.get(f"{GRAPH}/{path}", params=params, timeout=30)
    out = r.json()
    if "error" in out:
        falha(f"Graph error em {path}: {out['error'].get('message')}")
    return out


def descobrir_ig_id():
    contas = gget("me/accounts", fields="name,instagram_business_account")
    for pg in contas.get("data", []):
        iga = pg.get("instagram_business_account")
        if iga:
            print(f"[ig-report] IG business via página '{pg['name']}': {iga['id']}")
            return iga["id"]
    falha("Nenhuma página com conta Instagram Business vinculada. Vincule a Página ao @gymsiteintelligence primeiro.")


def main():
    if not TOKEN:
        falha("IG_GRAPH_TOKEN ausente no .env — gere o token no system user e cole lá.")
    ig = IG_ID or descobrir_ig_id()

    perfil = gget(ig, fields="username,followers_count,media_count")

    fim = datetime.now(timezone.utc)
    ini = fim - timedelta(days=7)
    metricas = {}
    try:
        ins = gget(f"{ig}/insights", metric="reach,profile_views,website_clicks",
                   period="day", since=int(ini.timestamp()), until=int(fim.timestamp()))
        for m in ins.get("data", []):
            metricas[m["name"]] = sum(v.get("value") or 0 for v in m.get("values", []))
    except SystemExit:
        raise
    except Exception as e:
        print(f"[ig-report] insights de conta indisponíveis ({e}) — seguindo com o resto")

    posts = gget(f"{ig}/media", fields="id,caption,media_type,timestamp,like_count,comments_count,permalink", limit=25)
    semana = [p for p in posts.get("data", [])
              if p.get("timestamp", "") >= ini.strftime("%Y-%m-%dT%H:%M:%S")]

    SAIDA.mkdir(parents=True, exist_ok=True)
    nome = SAIDA / f"report_{fim.strftime('%Y-%m-%d')}.md"
    linhas = [
        f"# Report semanal Instagram — @{perfil.get('username')} — {fim.strftime('%d/%m/%Y')}",
        "",
        f"- Seguidores: **{perfil.get('followers_count')}**",
        f"- Posts publicados na semana: **{len(semana)}** (meta: 3)",
        f"- Alcance (7d): **{metricas.get('reach', 'n/d')}**",
        f"- Visitas ao perfil (7d): **{metricas.get('profile_views', 'n/d')}**",
        f"- Cliques no link (7d): **{metricas.get('website_clicks', 'n/d')}**",
        "",
        "## Posts da semana",
        "",
    ]
    for p in semana:
        cap = (p.get("caption") or "").split("\n")[0][:80]
        linhas.append(f"- {p.get('timestamp','')[:10]} · {p.get('media_type')} · "
                      f"❤ {p.get('like_count',0)} · 💬 {p.get('comments_count',0)} · [{cap}]({p.get('permalink')})")
    if not semana:
        linhas.append("- Nenhum post na janela de 7 dias ⚠️ (meta da cadência: 3/semana)")

    nome.write_text("\n".join(linhas), encoding="utf-8")
    print(f"[ig-report] gerado: {nome}")
    print(json.dumps({"seguidores": perfil.get("followers_count"),
                      "posts_semana": len(semana), **metricas}, ensure_ascii=False))


if __name__ == "__main__":
    main()
