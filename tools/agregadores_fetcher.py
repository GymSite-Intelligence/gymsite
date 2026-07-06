"""
agregadores_fetcher.py — camada 3 do offer_mapper: oferta via agregadores
(Wellhub · Gurupass · TotalPass). SPEC: agents/specs/SPEC_OFERTA_AGREGADORES.md.

Determinístico, fail-soft, sem LLM. Sondagem 07/07 (caso Cocó):
- Wellhub: SSR puro → httpx captura modalidades, comodidades, tier+preço,
  rating próprio, horários, telefone e handle do IG.
- Gurupass: SSR parcial → modalidades + grade horária (preço é JS, fora).
- TotalPass: JS puro → só o snippet da busca `site:` (presença na rede).

Regras anti-lixo (lições da sugestão A3 rejeitada): keyword só conta em página
CUJO título casa o nome do concorrente; vocabulário único (_detectar_modalidades);
preço de agregador NUNCA vira preço de balcão (campo tier_agregador separado).
"""
from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(__file__).resolve().parent.parent / "competitor_cache"
_SEARCHAPI_URL = "https://www.searchapi.io/api/v1/search"
_FETCH_TIMEOUT_S = 12.0

_DOMINIOS = {
    "wellhub": "wellhub.com/pt-br/search/partners",
    "gurupass": "gurupass.com.br/detalhes-da-academia",
    "totalpass": "totalpass.com",
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", s).strip()


def _nome_casa(nome: str, titulo: str) -> bool:
    """Título do resultado precisa conter os tokens significativos do nome (≥2 chars,
    ignorando genéricos) — barreira anti-falso-positivo do dorking."""
    genericos = {"academia", "studio", "ct", "centro", "de", "do", "da", "fitness", "club"}
    tokens = [t for t in _norm(nome).split() if len(t) >= 2 and t not in genericos]
    if not tokens:
        return False
    alvo = _norm(titulo)
    acertos = sum(1 for t in tokens if t in alvo)
    return acertos >= max(1, len(tokens) - 1)


def _cache_path(fonte: str, chave: str) -> Path:
    limpo = re.sub(r"[^a-z0-9_-]+", "_", _norm(chave).replace(" ", "_"))[:80]
    return _CACHE_DIR / f"agg_{fonte}_{limpo}.json"


def _cache_load(fonte: str, chave: str) -> Optional[dict]:
    p = _cache_path(fonte, chave)
    try:
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    return None


def _cache_save(fonte: str, chave: str, payload: dict) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_path(fonte, chave).write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        logger.debug("cache agregador falhou ao salvar", exc_info=True)


def _texto_de_html(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    txt = re.sub(r"(?s)<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", txt).strip()


# ─── Parsers (operam sobre TEXTO, testáveis com fixture — sem rede) ─────────────

def parse_wellhub_texto(texto: str) -> dict:
    """Extrai os blocos estruturados da página de parceiro do Wellhub."""
    out: dict[str, Any] = {}
    m = re.search(r"A partir do plano (\w[\w+]*)", texto)
    preco = re.search(r"R\$\s?([\d.]+,\d{2})\s*/?\s*m[êe]s", texto)
    if m:
        out["tier_agregador"] = {
            "plano": m.group(1),
            "preco_mensal_brl": float(preco.group(1).replace(".", "").replace(",", ".")) if preco else None,
            "fonte": "wellhub",
            "observacao": "tier corporativo Wellhub — não é mensalidade de balcão",
        }
    r = re.search(r"(\d[.,]\d{1,2})\s*\(\s*([\d.]+)\s*Avalia", texto)
    if r:
        out["rating_agregador"] = {
            "nota": float(r.group(1).replace(",", ".")),
            "avaliacoes": int(r.group(2).replace(".", "")),
            "fonte": "wellhub",
        }
    ig = re.search(r"instagram\.com/([A-Za-z0-9_.]+)", texto)
    if ig and ig.group(1).lower() not in ("wellhub_br", "gympass"):
        out["instagram_handle"] = ig.group(1)
    com = re.search(r"O que este parceiro oferece(.{10,900}?)(Hor[áa]rio de funcionamento|---)", texto)
    if com:
        out["comodidades"] = [c.strip() for c in re.split(
            r"(?<=[a-zâãéíóú]) (?=[A-ZÁÂÃÉÍÓÚW])", com.group(1).strip()) if 2 < len(c.strip()) < 60]
    return out


def parse_gurupass_texto(texto: str) -> dict:
    """Gurupass: modalidades vêm na descrição/chips (o preço é JS — fora)."""
    return {"fonte_extra": "gurupass"}


# ─── Descoberta + coleta ────────────────────────────────────────────────────────

def _buscar_url_parceiro(fonte: str, nome: str, cidade: str) -> Optional[dict]:
    """SearchAPI (engine=google) `site:<dominio> "<nome>" <cidade>`; valida o título
    contra o nome. Cacheado em disco (inclusive resultado negativo)."""
    chave = f"{nome} {cidade}"
    cached = _cache_load(fonte, chave)
    if cached is not None:
        return cached.get("hit") or None
    key = (os.getenv("SEARCHAPI_KEY") or "").strip()
    if not key:
        return None
    try:
        r = httpx.get(_SEARCHAPI_URL, params={
            "engine": "google", "gl": "br", "hl": "pt-br",
            "q": f'site:{_DOMINIOS[fonte]} "{nome}" {cidade}',
        }, headers={"Authorization": f"Bearer {key}"}, timeout=_FETCH_TIMEOUT_S)
        organicos = (r.json() or {}).get("organic_results") or []
    except Exception as exc:
        logger.debug("busca agregador %s falhou: %s", fonte, exc)
        return None
    hit = None
    for res in organicos[:5]:
        titulo = str(res.get("title") or "")
        if _nome_casa(nome, titulo):
            hit = {"url": res.get("link"), "titulo": titulo,
                   "snippet": str(res.get("snippet") or "")}
            break
    _cache_save(fonte, chave, {"hit": hit})
    return hit


async def coletar_agregadores(
    client: httpx.AsyncClient, nome: str, cidade: str | None
) -> dict:
    """Coleta fail-soft nas 3 fontes. Retorna {textos: [...], extras: {...},
    fontes_ok: [...]} pro mapear_oferta_concorrente somar ao blob de análise."""
    import asyncio

    textos: list[str] = []
    extras: dict[str, Any] = {}
    fontes_ok: list[str] = []
    cidade = cidade or ""
    for fonte in ("wellhub", "gurupass", "totalpass"):
        try:
            hit = await asyncio.to_thread(_buscar_url_parceiro, fonte, nome, cidade)
            if not hit:
                continue
            if fonte == "totalpass":
                textos.append(hit.get("snippet") or "")
                extras["totalpass_presente"] = True
                fontes_ok.append(fonte)
                continue
            resp = await client.get(hit["url"], follow_redirects=True, timeout=_FETCH_TIMEOUT_S)
            if resp.status_code != 200 or len(resp.text) < 500:
                continue
            texto = _texto_de_html(resp.text)
            textos.append(texto)
            fontes_ok.append(fonte)
            if fonte == "wellhub":
                extras.update(parse_wellhub_texto(texto))
        except Exception as exc:
            logger.debug("agregador %s falhou p/ %s: %s", fonte, nome, exc)
    return {"textos": textos, "extras": extras, "fontes_ok": fontes_ok}
