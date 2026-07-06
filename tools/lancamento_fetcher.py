"""
lancamento_fetcher.py — refino DETERMINÍSTICO da Janela de Entrada (T+24).
SPEC: agents/specs/SPEC_REFINO_LANCAMENTO_DETERMINISTICO.md.

Inverte a ordem do refino: página do lançamento via SearchAPI+httpx PRIMEIRO
(barato → roda em TODAS as obras residenciais), grounding LLM vira fallback.
Páginas de lançamento são SSR/SEO por natureza (construtora quer ser indexada).

Gate anti-falso-positivo: o texto da página precisa conter o LOGRADOURO da obra
(ou o CEP) — mesmo rigor do gate do grounding, sem LLM. Retorna no MESMO contrato
de refinar_demanda_via_lancamento (unidades_exatas, areas_plantas, preco_base…).
"""
from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Callable, Optional

import httpx

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(__file__).resolve().parent.parent / "competitor_cache"
_SEARCHAPI_URL = "https://www.searchapi.io/api/v1/search"
_TIMEOUT_S = 12.0

_RX_UNIDADES = re.compile(
    r"(\d{2,4})\s*(?:unidades|aptos?\b|apartamentos|resid[êe]ncias)", re.I)
_RX_PLANTAS_FAIXA = re.compile(
    r"(\d{2,3})(?:[.,]\d)?\s*(?:m²|m2)\s*(?:a|à|até|e)\s*(\d{2,3})(?:[.,]\d)?\s*(?:m²|m2)?", re.I)
_RX_PLANTA_UNICA = re.compile(r"(\d{2,3})(?:[.,]\d)?\s*(?:m²|m2)", re.I)
_RX_PRECO = re.compile(r"R\$\s*([\d]{3}(?:\.\d{3}){1,2})(?:,\d{2})?")
_RX_ENTREGA = re.compile(
    r"(?:entrega|previs[ãa]o|conclus[ãa]o|habite-se)[^.\n]{0,60}?(20\d{2})", re.I)
_KW_FITNESS = ("academia", "fitness", "espaço fitness", "espaco fitness", "wellness")
_KW_RESIDENCIAL = ("apartament", "residencial", "studio", "dormit", "suíte", "suite", "quarto")

_PRECO_IMOVEL_MIN, _PRECO_IMOVEL_MAX = 100_000, 100_000_000


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", re.sub(r"\s+", " ", s)).strip()


def _texto_de_html(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    return re.sub(r"\s+", " ", re.sub(r"(?s)<[^>]+>", " ", html)).strip()


# ─── Parser (puro, testável com fixture) ───────────────────────────────────────

def parse_pagina_lancamento(texto: str) -> dict:
    """Extrai unidades/plantas/preço/entrega/fitness do TEXTO da página. Só devolve
    o que ACHOU — sem inventar (campo ausente = None, proxy continua valendo)."""
    out: dict[str, Any] = {}
    m = _RX_UNIDADES.search(texto)
    if m:
        n = int(m.group(1))
        if 4 <= n <= 5000:
            out["unidades_exatas"] = n
    f = _RX_PLANTAS_FAIXA.search(texto)
    if f:
        a, b = float(f.group(1)), float(f.group(2))
        if 15 <= a < b <= 800:
            out["areas_plantas"] = [a, b]
    elif (u := _RX_PLANTA_UNICA.search(texto)):
        a = float(u.group(1))
        if 15 <= a <= 800:
            out["areas_plantas"] = [a]
    precos = []
    for p in _RX_PRECO.findall(texto):
        try:
            v = float(p.replace(".", ""))
        except ValueError:
            continue
        if _PRECO_IMOVEL_MIN <= v <= _PRECO_IMOVEL_MAX:
            precos.append(v)
    if precos:
        out["preco_base"] = {"min": min(precos), "max": max(precos),
                             "fonte": "pagina_lancamento"}
    e = _RX_ENTREGA.search(texto)
    if e:
        out["previsao_entrega"] = e.group(1)
    t = texto.lower()
    out["amenidade_fitness"] = any(k in t for k in _KW_FITNESS)
    if any(k in t for k in _KW_RESIDENCIAL):
        out["tipologia"] = "residencial"
    return out


def _pagina_casa_obra(texto: str, obra: dict) -> bool:
    """Gate: a página precisa citar o LOGRADOURO (≥6 chars) ou o CEP da obra —
    mesmo rigor do gate do grounding, determinístico."""
    alvo = _norm(texto)
    log = _norm(obra.get("logradouro") or "")
    if len(log) >= 6 and log in alvo:
        return True
    cep = re.sub(r"\D", "", str(obra.get("cep") or ""))
    if len(cep) == 8 and (cep in re.sub(r"\D", "", texto[:20000])):
        return True
    return False


# ─── Descoberta + coleta ───────────────────────────────────────────────────────

def _cache_path(chave: str) -> Path:
    limpo = re.sub(r"[^a-z0-9_-]+", "_", _norm(chave).replace(" ", "_"))[:80]
    return _CACHE_DIR / f"lanc_{limpo}.json"


def _buscar_paginas(obra: dict) -> list[dict]:
    """SearchAPI google: endereço lidera a query (nome CNO é SPE/ruído). Cacheado."""
    log = (obra.get("logradouro") or "").strip()
    num = str(obra.get("numero_logradouro") or "").strip()
    bairro = (obra.get("bairro") or "").strip()
    cidade = (obra.get("cidade") or "").strip()
    chave = f"{log} {num} {bairro} {cidade}"
    p = _cache_path(chave)
    try:
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8")).get("resultados") or []
    except Exception:
        pass
    key = (os.getenv("SEARCHAPI_KEY") or "").strip()
    if not key or not log:
        return []
    try:
        r = httpx.get(_SEARCHAPI_URL, params={
            "engine": "google", "gl": "br", "hl": "pt-br",
            "q": f'lançamento apartamento "{log}" {bairro} {cidade} unidades planta',
        }, headers={"Authorization": f"Bearer {key}"}, timeout=_TIMEOUT_S)
        resultados = [
            {"url": x.get("link"), "titulo": x.get("title"), "snippet": x.get("snippet")}
            for x in ((r.json() or {}).get("organic_results") or [])[:5]
        ]
    except Exception as exc:
        logger.debug("busca lançamento falhou: %s", exc)
        return []
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"resultados": resultados}, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return resultados


def refinar_lancamento_deterministico(
    obra: dict,
    *,
    _buscar_fn: Optional[Callable[[dict], list[dict]]] = None,
    _fetch_fn: Optional[Callable[[str], Optional[str]]] = None,
) -> Optional[dict]:
    """Tenta refinar a obra pela página do lançamento (até 3 candidatas). Retorna
    dict no contrato do refino (confianca alta, auditado, fonte_url) ou None —
    None sinaliza ao caller que o fallback (grounding LLM) pode tentar."""
    buscar = _buscar_fn or _buscar_paginas
    fetch = _fetch_fn or _fetch_url
    try:
        for res in (buscar(obra) or [])[:3]:
            url = res.get("url")
            if not url:
                continue
            html = fetch(url)
            if not html or len(html) < 500:
                continue
            texto = _texto_de_html(html)
            if not _pagina_casa_obra(texto, obra):
                continue
            ext = parse_pagina_lancamento(texto)
            if not ext.get("unidades_exatas") and not ext.get("areas_plantas"):
                continue
            ext.update({
                "empreendimento": (res.get("titulo") or "").split("|")[0].split(" - ")[0].strip() or None,
                "fonte_url": url,
                "fontes": [{"url": url, "via": "pagina_lancamento_deterministica"}],
                "confianca": "alta",
                "metodo_match": "endereco_na_pagina",
                "auditado": True,
                "cruzado": False,
            })
            return ext
    except Exception:
        logger.debug("refino determinístico falhou p/ %s", obra.get("nome"), exc_info=True)
    return None


def radar_pre_lancamentos(
    bairro: str,
    cidade: str,
    *,
    obras_cno: list[dict] | None = None,
    max_itens: int = 4,
    _buscar_fn: Optional[Callable[[str], list[dict]]] = None,
    _fetch_fn: Optional[Callable[[str], Optional[str]]] = None,
) -> list[dict]:
    """Task #12: empreendimentos em VENDA que ainda não têm CNO (pré-lançamento) —
    demanda futura invisível pro censo registral. REGRA DURA: sai em seção separada
    e NUNCA soma nos totais (sem registro = sem carimbo de auditabilidade).

    Dedupe contra as obras do CNO por logradouro/nome; valida que a página cita o
    bairro-alvo. Fail-soft total: erro = lista vazia."""
    buscar = _buscar_fn or _buscar_radar
    fetch = _fetch_fn or _fetch_url
    if not bairro or not cidade:
        return []
    ja_no_cno: set[str] = set()
    for ob in (obras_cno or []):
        for campo in ("logradouro", "nome", "empreendimento"):
            v = _norm(str(ob.get(campo) or ""))
            if len(v) >= 6:
                ja_no_cno.add(v)
    radar: list[dict] = []
    try:
        for res in (buscar(f'lançamento apartamento "{bairro}" {cidade} unidades planta breve') or [])[:8]:
            url = res.get("url")
            titulo = str(res.get("titulo") or "")
            if not url:
                continue
            t_norm = _norm(titulo)
            if any(c and c in t_norm for c in ja_no_cno):
                continue
            html = fetch(url)
            if not html or len(html) < 500:
                continue
            texto = _texto_de_html(html)
            if _norm(bairro) not in _norm(texto):
                continue
            blob_norm = _norm(texto[:4000])
            if any(c and c in blob_norm for c in ja_no_cno):
                continue
            ext = parse_pagina_lancamento(texto)
            if not ext.get("unidades_exatas") and not ext.get("areas_plantas"):
                continue
            radar.append({
                "empreendimento": titulo.split("|")[0].split(" - ")[0].strip()[:40] or "—",
                "unidades_est": ext.get("unidades_exatas"),
                "areas_plantas": ext.get("areas_plantas"),
                "preco_base": ext.get("preco_base"),
                "previsao_entrega": ext.get("previsao_entrega"),
                "fonte_url": url,
                "fora_dos_totais": True,
                "motivo": "sem registro CNO (pré-lançamento) — informativo, não soma demanda",
            })
            if len(radar) >= max_itens:
                break
    except Exception:
        logger.debug("radar pré-lançamentos falhou p/ %s/%s", bairro, cidade, exc_info=True)
    return radar


def _buscar_radar(query: str) -> list[dict]:
    key = (os.getenv("SEARCHAPI_KEY") or "").strip()
    if not key:
        return []
    chave = query
    p = _cache_path(f"radar {chave}")
    try:
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8")).get("resultados") or []
    except Exception:
        pass
    try:
        r = httpx.get(_SEARCHAPI_URL, params={
            "engine": "google", "gl": "br", "hl": "pt-br", "q": query,
        }, headers={"Authorization": f"Bearer {key}"}, timeout=_TIMEOUT_S)
        resultados = [
            {"url": x.get("link"), "titulo": x.get("title"), "snippet": x.get("snippet")}
            for x in ((r.json() or {}).get("organic_results") or [])[:8]
        ]
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"resultados": resultados}, ensure_ascii=False), encoding="utf-8")
        return resultados
    except Exception as exc:
        logger.debug("busca radar falhou: %s", exc)
        return []


def _fetch_url(url: str) -> Optional[str]:
    try:
        r = httpx.get(url, follow_redirects=True, timeout=_TIMEOUT_S, headers={
            "User-Agent": "Mozilla/5.0 (compatible; GymSiteBot/1.0)",
            "Accept-Language": "pt-BR,pt;q=0.9",
        })
        return r.text if r.status_code == 200 else None
    except Exception:
        return None
