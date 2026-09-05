"""Portuguese Wikipedia / Wikidata context for a Brazilian municipality.

Complementary A0 source — always attempted alongside market_bundle, never a
fallback for it, and never canonical for parque/score/ticket/MRLR numbers.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

logger = logging.getLogger("gymsite.wikipedia_municipio")

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "wiki_municipios"
DEFAULT_TTL_DAYS = 30
TIMEOUT_S = 12.0
RETRY_BACKOFF_S = 1.5
SECTION_MAX_CHARS = 1200
USER_AGENT = "GymSiteIntelligence/1.x (A0-wiki; +https://vectracargo.com.br)"
MW_API = "https://pt.wikipedia.org/w/api.php"
WD_API = "https://www.wikidata.org/w/api.php"
MUNICIPIO_BRASIL_QID = "Q3184121"

BUNDLE_TICKET_FIELDS = (
    "ticket_medio_mercado",
    "aluguel_medio_m2",
    "renda_media_bairro",
)
WIKI_FORBIDDEN_PREFIXES = ("parque_", "score_")

# Closed UF set — used only to disambiguate Wikidata P131. CE verified Q40123.
UF_WIKIDATA_QID: dict[str, str] = {
    "AC": "Q40780",
    "AL": "Q40885",
    "AP": "Q40130",
    "AM": "Q40040",
    "BA": "Q40430",
    "CE": "Q40123",
    "DF": "Q119158",
    "ES": "Q43233",
    "GO": "Q41587",
    "MA": "Q42362",
    "MT": "Q42824",
    "MS": "Q43319",
    "MG": "Q39109",
    "PA": "Q39517",
    "PB": "Q38088",
    "PR": "Q15499",
    "PE": "Q40942",
    "PI": "Q42722",
    "RJ": "Q41428",
    "RN": "Q43255",
    "RS": "Q40030",
    "RO": "Q43235",
    "RR": "Q42508",
    "SC": "Q41115",
    "SP": "Q175",
    "SE": "Q43783",
    "TO": "Q43695",
}
UF_NOME: dict[str, str] = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AP": "Amapá",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Pará",
    "PB": "Paraíba",
    "PR": "Paraná",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondônia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "São Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins",
}

_INFOBOX_QUALITATIVE = (
    "gentílico",
    "gentilico",
    "apelido",
    "lema",
    "prefeito",
    "partido",
    "estado",
    "mesorregião",
    "mesorregiao",
    "microrregião",
    "microrregiao",
    "região_metropolitana",
    "regiao_metropolitana",
    "vizinhos",
    "clima",
    "padroeiro",
)
_INFOBOX_METRIC = {
    "fundação": "fundacao",
    "fundacao": "fundacao",
    "área": "area_km2",
    "area": "area_km2",
    "população": "populacao",
    "populacao": "populacao",
    "altitude": "altitude_m",
    "idh": "idh",
    "pib": "pib",
    "pib_per_capita": "pib_per_capita",
    "dist_capital": "dist_capital_km",
}
_WD_CLAIM_KEYS = {
    "P571": "fundacao",
    "P131": "localizado_em",
    "P2046": "area_km2",
    "P1082": "populacao",
    "P2044": "altitude_m",
    "P47": "limitrofes",
    "P856": "site_oficial",
}

_LAST_SNAPSHOT: dict[str, Any] | None = None
_FRONT_RE = re.compile(
    r"<!--\s*wikipedia_municipio\s+"
    r"status=(?P<status>ok|missing|error)\s+"
    r"cidade=(?P<cidade>\S*)\s+"
    r"uf=(?P<uf>\S*)\s+"
    r"qid=(?P<qid>\S*)\s+"
    r"url=(?P<url>\S*)\s+"
    r"retrieved_at=(?P<retrieved_at>\S*)\s*-->",
    re.IGNORECASE,
)


def wiki_slug(cidade: str, uf: str) -> str:
    return f"{cidade.strip().lower()}_{uf.strip().upper()}"


def wiki_cache_path(cidade: str, uf: str) -> Path:
    return CACHE_DIR / f"{wiki_slug(cidade, uf)}.json"


def last_snapshot() -> dict[str, Any] | None:
    return _LAST_SNAPSHOT


def snapshot_from_markdown(md: str) -> dict[str, Any] | None:
    m = _FRONT_RE.search(md or "")
    if not m:
        return None
    return {
        "status": m.group("status").lower(),
        "cidade": m.group("cidade"),
        "uf": m.group("uf"),
        "qid": m.group("qid") or "",
        "url": m.group("url") or "",
        "retrieved_at": m.group("retrieved_at") or "",
        "fonte": "wikipedia_pt + wikidata",
    }


def snapshot_for_a0(tool_response: Any = None) -> dict[str, Any] | None:
    if isinstance(_LAST_SNAPSHOT, dict):
        return _LAST_SNAPSHOT
    if isinstance(tool_response, str):
        return snapshot_from_markdown(tool_response)
    return None


def apply_contexto_local_wiki(inner: dict[str, Any], snap: dict[str, Any]) -> bool:
    """Attach contexto_local_wiki. Never writes parque_*/score_* or bundle ticket."""
    if not isinstance(inner, dict) or not isinstance(snap, dict):
        return False
    ticket_before = {k: inner.get(k) for k in BUNDLE_TICKET_FIELDS}
    forbidden_before = {
        k: inner.get(k)
        for k in inner
        if k.startswith(WIKI_FORBIDDEN_PREFIXES)
    }
    status = str(snap.get("status") or "error")
    inner["contexto_local_wiki"] = {
        "status": status,
        "url": snap.get("url") or "",
        "qid": snap.get("qid") or "",
        "lead": snap.get("lead") or "",
        "insights_wiki": list(snap.get("insights_wiki") or []),
        "infobox_qualitativo": dict(snap.get("infobox_qualitativo") or {}),
        "metricas_referencia": list(snap.get("metricas_referencia") or []),
        "fonte": "wikipedia_pt + wikidata" if status == "ok" else (snap.get("fonte") or "wikipedia"),
        "retrieved_at": snap.get("retrieved_at") or "",
    }
    if status == "ok":
        fonte = str(inner.get("fonte") or "")
        if "wikipedia" not in fonte.lower():
            inner["fonte"] = f"{fonte} + wikipedia".strip(" +") if fonte else "wikipedia"
    for k, v in ticket_before.items():
        if v is not None:
            inner[k] = v
    for k, v in forbidden_before.items():
        inner[k] = v
    return True


def carregar_wikipedia_municipio(cidade: str, uf: str, *, bairro: str | None = None) -> str:
    """A0 tool: municipal Wikipedia/Wikidata context as markdown (ok|missing|error)."""
    snap = fetch_wikipedia_municipio(cidade, uf, bairro=bairro)
    return snapshot_to_markdown(snap)


def fetch_wikipedia_municipio(
    cidade: str,
    uf: str,
    *,
    bairro: str | None = None,
) -> dict[str, Any]:
    """Structured snapshot for cache + a0_tool_snapshots. `bairro` unused in v1."""
    global _LAST_SNAPSHOT
    _ = bairro
    cidade_n = (cidade or "").strip()
    uf_n = (uf or "").strip().upper()
    retrieved = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not cidade_n or not uf_n:
        snap = _empty_snapshot(cidade_n, uf_n, "error", retrieved, erro="cidade_ou_uf_vazios")
        _LAST_SNAPSHOT = snap
        return snap

    path = wiki_cache_path(cidade_n, uf_n)
    force = (os.environ.get("WIKI_MUNICIPIO_FORCE_REFRESH") or "").strip() in {"1", "true", "TRUE"}
    if not force:
        cached = _read_cache(path)
        if cached is not None:
            cached.setdefault("cache", {})
            cached["cache"] = {"hit": True, "path": str(path)}
            _record_telemetry("wikipedia_mediawiki", cache_hit=True, latency_ms=0.0)
            _LAST_SNAPSHOT = cached
            return cached

    t0 = time.perf_counter()
    try:
        snap = _fetch_live(cidade_n, uf_n, retrieved)
    except Exception as exc:
        logger.warning("wikipedia_municipio falhou %s/%s: %s", cidade_n, uf_n, exc)
        snap = _empty_snapshot(
            cidade_n,
            uf_n,
            "error",
            retrieved,
            erro=f"{type(exc).__name__}: {exc}",
        )
    snap["cache"] = {"hit": False, "path": str(path)}
    snap["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    if snap.get("status") == "ok":
        _write_cache(path, snap)
    _LAST_SNAPSHOT = snap
    return snap


def snapshot_to_markdown(snap: dict[str, Any]) -> str:
    status = str(snap.get("status") or "error")
    header = (
        f"<!-- wikipedia_municipio status={status} "
        f"cidade={snap.get('cidade') or ''} uf={snap.get('uf') or ''} "
        f"qid={snap.get('qid') or ''} url={snap.get('url') or ''} "
        f"retrieved_at={snap.get('retrieved_at') or ''} -->"
    )
    if status == "missing":
        return (
            f"{header}\n\n"
            f"**wikipedia_municipio** sem página de município para "
            f"{snap.get('cidade')}/{snap.get('uf')}. Não bloqueia o pipeline."
        )
    if status != "ok":
        erro = snap.get("erro") or "falha na consulta"
        return (
            f"{header}\n\n"
            f"**wikipedia_municipio** erro: {erro}. "
            "Não bloqueia o pipeline. Não usar como fonte de número canônico."
        )

    lines = [header, "", f"# {snap.get('title') or snap.get('cidade')}", ""]
    lead = (snap.get("lead") or "").strip()
    if lead:
        lines.extend(["## Lead", lead, ""])

    info = snap.get("infobox_qualitativo") or {}
    if info:
        lines.append("## Infobox qualitativo")
        for k, v in info.items():
            if v:
                lines.append(f"- {k}: {v}")
        lines.append("")

    secoes = snap.get("secoes") or {}
    for key, title in (
        ("economia", "Economia"),
        ("geografia", "Geografia"),
        ("historia", "História"),
        ("aspectos_sociais", "Aspectos sociais"),
    ):
        body = (secoes.get(key) or "").strip()
        if body:
            lines.extend([f"## {title}", body, ""])

    metricas = snap.get("metricas_referencia") or []
    if metricas:
        lines.append("## Métricas de referência (display_only)")
        lines.append("Não usar como A2/IBGE, CNPJ, MRLR ou score.")
        for m in metricas:
            if not isinstance(m, dict):
                continue
            lines.append(
                f"- {m.get('chave')}: {m.get('valor')} · {m.get('fonte')} · {m.get('uso') or 'display_only'}"
            )
        lines.append("")

    lines.append("## Fontes")
    url = snap.get("url") or ""
    qid = snap.get("qid") or ""
    if url:
        lines.append(f"- {url}")
    if qid:
        lines.append(f"- https://www.wikidata.org/wiki/{qid}")
    lines.append("")
    return "\n".join(lines)


def _empty_snapshot(
    cidade: str,
    uf: str,
    status: str,
    retrieved: str,
    *,
    erro: str | None = None,
) -> dict[str, Any]:
    snap: dict[str, Any] = {
        "status": status,
        "cidade": cidade,
        "uf": uf,
        "qid": "",
        "url": "",
        "title": "",
        "lead": "",
        "infobox_qualitativo": {},
        "secoes": {},
        "metricas_referencia": [],
        "insights_wiki": [],
        "fonte": "wikipedia",
        "retrieved_at": retrieved,
        "cache": {"hit": False, "path": ""},
        "lacunas": [],
    }
    if status == "missing":
        snap["lacunas"] = ["pagina_municipio_nao_encontrada"]
    if erro:
        snap["erro"] = erro
        snap["lacunas"] = list(snap["lacunas"]) + ["erro_http"]
    return snap


def _max_age_days() -> int:
    raw = (os.environ.get("WIKI_MUNICIPIO_MAX_AGE_DAYS") or "").strip()
    if not raw:
        return DEFAULT_TTL_DAYS
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_TTL_DAYS


def _parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _read_cache(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or data.get("status") != "ok":
        return None
    ts = _parse_ts(str(data.get("retrieved_at") or ""))
    if ts is None:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - ts.astimezone(timezone.utc)
    if age.total_seconds() > _max_age_days() * 86400:
        return None
    return data


def _write_cache(path: Path, snap: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        logger.warning("wikipedia_municipio: falha ao gravar cache %s", path)


def _record_telemetry(sku: str, *, cache_hit: bool, latency_ms: float, ok: bool = True) -> None:
    provider = "wikidata" if "wikidata" in sku else "wikipedia_mediawiki"
    logger.info(
        "wikipedia_municipio provider=%s sku=%s cache_hit=%s latency_ms=%.0f ok=%s custo=0",
        provider,
        sku,
        cache_hit,
        latency_ms,
        ok,
    )
    if cache_hit:
        return
    try:
        from tools.api_cost_tracker import track_api_call

        with track_api_call("carregar_wikipedia_municipio", sku, 1):
            pass
    except Exception:
        pass


def _http_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    import httpx

    sku = "wikipedia_wikidata" if "wikidata.org" in url else "wikipedia_mediawiki"
    t0 = time.perf_counter()
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            with httpx.Client(
                timeout=TIMEOUT_S,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                follow_redirects=True,
            ) as client:
                resp = client.get(url, params=params)
            if resp.status_code in {429, 503} and attempt == 0:
                time.sleep(RETRY_BACKOFF_S)
                continue
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, dict):
                raise ValueError("resposta JSON inválida")
            _record_telemetry(
                sku,
                cache_hit=False,
                latency_ms=(time.perf_counter() - t0) * 1000,
            )
            return data
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            code = exc.response.status_code if exc.response is not None else 0
            if code in {429, 503} and attempt == 0:
                time.sleep(RETRY_BACKOFF_S)
                continue
            break
        except httpx.TimeoutException as exc:
            last_exc = exc
            break
        except Exception as exc:
            last_exc = exc
            break
    _record_telemetry(
        sku,
        cache_hit=False,
        latency_ms=(time.perf_counter() - t0) * 1000,
        ok=False,
    )
    raise last_exc or RuntimeError("wikipedia http failed")


def _first_page(payload: dict[str, Any]) -> dict[str, Any] | None:
    pages = (payload.get("query") or {}).get("pages") or {}
    if not isinstance(pages, dict) or not pages:
        return None
    page = next(iter(pages.values()))
    return page if isinstance(page, dict) else None


def _is_missing_page(page: dict[str, Any] | None) -> bool:
    if not page:
        return True
    if page.get("missing") is not None:
        return True
    try:
        return int(page.get("pageid") or 0) < 0
    except (TypeError, ValueError):
        return True


def _is_disambiguation(page: dict[str, Any]) -> bool:
    props = page.get("pageprops") or {}
    if isinstance(props, dict) and "disambiguation" in props:
        return True
    title = str(page.get("title") or "").lower()
    if "desambiguação" in title or "desambiguacao" in title:
        return True
    for cat in page.get("categories") or []:
        if isinstance(cat, dict) and "desambiguação" in str(cat.get("title") or "").lower():
            return True
    return False


def _mw_query(title: str) -> dict[str, Any] | None:
    data = _http_json(
        MW_API,
        {
            "action": "query",
            "titles": title,
            "redirects": "1",
            "prop": "extracts|pageprops|info|revisions|categories",
            "explaintext": "1",
            "exsectionformat": "plain",
            "ppprop": "wikibase_item|disambiguation",
            "inprop": "url",
            "rvprop": "content",
            "rvslots": "main",
            "cllimit": "20",
            "format": "json",
        },
    )
    return _first_page(data)


def _wd_search(cidade: str) -> list[str]:
    data = _http_json(
        WD_API,
        {
            "action": "wbsearchentities",
            "search": cidade,
            "language": "pt",
            "uselang": "pt",
            "type": "item",
            "limit": "8",
            "format": "json",
        },
    )
    ids: list[str] = []
    for hit in data.get("search") or []:
        if isinstance(hit, dict) and hit.get("id"):
            ids.append(str(hit["id"]))
    return ids


def _wd_entities(ids: list[str], props: str) -> dict[str, Any]:
    if not ids:
        return {}
    data = _http_json(
        WD_API,
        {
            "action": "wbgetentities",
            "ids": "|".join(ids),
            "props": props,
            "languages": "pt",
            "format": "json",
        },
    )
    ents = data.get("entities") or {}
    return ents if isinstance(ents, dict) else {}


def _p31_ids(entity: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for claim in (entity.get("claims") or {}).get("P31") or []:
        if not isinstance(claim, dict):
            continue
        val = ((claim.get("mainsnak") or {}).get("datavalue") or {}).get("value") or {}
        qid = val.get("id") if isinstance(val, dict) else None
        if qid:
            out.add(str(qid))
    return out


def _p131_ids(entity: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for claim in (entity.get("claims") or {}).get("P131") or []:
        if not isinstance(claim, dict):
            continue
        val = ((claim.get("mainsnak") or {}).get("datavalue") or {}).get("value") or {}
        qid = val.get("id") if isinstance(val, dict) else None
        if qid:
            out.add(str(qid))
    return out


def _resolve_via_wikidata(cidade: str, uf: str) -> dict[str, Any] | None:
    uf_qid = UF_WIKIDATA_QID.get(uf)
    uf_nome = (UF_NOME.get(uf) or "").lower()
    for qid in _wd_search(cidade):
        ents = _wd_entities([qid], "claims|sitelinks|labels")
        ent = ents.get(qid) or {}
        if MUNICIPIO_BRASIL_QID not in _p31_ids(ent):
            continue
        p131 = _p131_ids(ent)
        label_ok = False
        if uf_qid and uf_qid in p131:
            label_ok = True
        elif uf_nome:
            labs = _wd_entities(list(p131), "labels") if p131 else {}
            label_ok = any(
                uf_nome in str((e.get("labels") or {}).get("pt", {}).get("value") or "").lower()
                for e in labs.values()
                if isinstance(e, dict)
            )
        if not label_ok:
            continue
        title = ((ent.get("sitelinks") or {}).get("ptwiki") or {}).get("title")
        if title:
            page = _mw_query(str(title))
            if page and not _is_missing_page(page) and not _is_disambiguation(page):
                return page
    return None


def _resolve_page(cidade: str, uf: str) -> dict[str, Any] | None:
    titles = [cidade, f"{cidade} (município)", f"{cidade} ({uf})", f"{cidade} ({UF_NOME.get(uf, uf)})"]
    seen: set[str] = set()
    for title in titles:
        key = title.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        page = _mw_query(title)
        if _is_missing_page(page):
            continue
        assert page is not None
        if _is_disambiguation(page):
            continue
        return page
    return _resolve_via_wikidata(cidade, uf)


def _wikitext(page: dict[str, Any]) -> str:
    revs = page.get("revisions") or []
    if not revs or not isinstance(revs[0], dict):
        return ""
    slot = ((revs[0].get("slots") or {}).get("main") or {})
    return str(slot.get("*") or revs[0].get("*") or "")


def _clean_wiki(val: str) -> str:
    text = val or ""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"\{\{dtlink\|(\d+)\|(\d+)\|(\d+)[^}]*\}\}", r"\1/\2/\3", text)
    text = re.sub(r"\{\{formatnum:([^}]+)\}\}", r"\1", text)
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S | re.I)
    text = re.sub(r"<ref[^/]*/>", "", text, flags=re.I)
    for _ in range(6):
        nxt = re.sub(r"\{\{[^{}]*\}\}", "", text)
        if nxt == text:
            break
        text = nxt
    text = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = text.replace("'''", "").replace("''", "")
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_infobox(wikitext: str) -> dict[str, str]:
    m = re.search(r"\{\{\s*Info/Munic[^\n]*", wikitext or "", flags=re.I)
    if not m:
        return {}
    start = m.start()
    depth = 0
    i = start
    while i < len(wikitext) - 1:
        chunk = wikitext[i : i + 2]
        if chunk == "{{":
            depth += 1
            i += 2
            continue
        if chunk == "}}":
            depth -= 1
            i += 2
            if depth <= 0:
                break
            continue
        i += 1
    body = wikitext[start:i]
    fields: dict[str, str] = {}
    for line in body.splitlines():
        mm = re.match(r"\s*\|\s*([^=|]+?)\s*=\s*(.*)$", line)
        if not mm:
            continue
        key = mm.group(1).strip().lower()
        val = _clean_wiki(mm.group(2))
        if key and val:
            fields[key] = val
    return fields


def _truncate(text: str, limit: int = SECTION_MAX_CHARS) -> str:
    raw = re.sub(r"\s+", " ", (text or "")).strip()
    if len(raw) <= limit:
        return raw
    cut = raw[:limit]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" .,;") + "…"


def _split_sections(extract: str) -> dict[str, str]:
    text = extract or ""
    headings = {
        "historia": re.compile(r"^Hist[oó]ria\s*$", re.M),
        "geografia": re.compile(r"^Geografia\s*$", re.M),
        "economia": re.compile(r"^Economia\s*$", re.M),
        "aspectos_sociais": re.compile(r"^Aspectos sociais\s*$", re.M | re.I),
    }
    found: list[tuple[int, str]] = []
    for key, rx in headings.items():
        m = rx.search(text)
        if m:
            found.append((m.start(), key))
    found.sort()
    out: dict[str, str] = {}
    for idx, (pos, key) in enumerate(found):
        m = headings[key].search(text, pos)
        start = m.end() if m else pos
        end = found[idx + 1][0] if idx + 1 < len(found) else len(text)
        out[key] = _truncate(text[start:end])
    return out


def _lead_from_extract(extract: str) -> str:
    parts = re.split(r"\n{2,}", extract or "", maxsplit=1)
    lead = parts[0] if parts else ""
    # Drop heading-only first chunk
    if re.match(r"^(Etimologia|Hist[oó]ria|Geografia)\s*$", lead.strip()):
        return _truncate(extract, 900)
    return _truncate(lead, 900)


def _claim_value(claim: dict[str, Any]) -> Any:
    snak = claim.get("mainsnak") or {}
    dv = snak.get("datavalue") or {}
    val = dv.get("value")
    typ = dv.get("type")
    if typ == "wikibase-entityid" and isinstance(val, dict):
        return val.get("id")
    if typ == "quantity" and isinstance(val, dict):
        amt = str(val.get("amount") or "").lstrip("+")
        return amt
    if typ == "time" and isinstance(val, dict):
        return str(val.get("time") or "")[:10].lstrip("+")
    if typ == "string" or isinstance(val, str):
        return val
    return None


def _claim_time(claim: dict[str, Any]) -> str:
    for qid, quals in (claim.get("qualifiers") or {}).items():
        if qid != "P585" or not quals:
            continue
        t = ((quals[0].get("datavalue") or {}).get("value") or {}).get("time")
        if t:
            return str(t)
    return ""


def _pick_claims(claims: dict[str, Any], pid: str) -> list[Any]:
    items = claims.get(pid) or []
    if pid == "P1082" and items:
        best, best_t = items[0], ""
        for c in items:
            if not isinstance(c, dict):
                continue
            t = _claim_time(c)
            if t >= best_t:
                best, best_t = c, t
        return [_claim_value(best)]
    out: list[Any] = []
    for c in items:
        if isinstance(c, dict):
            v = _claim_value(c)
            if v is not None:
                out.append(v)
    return out


def _metrica(chave: str, valor: Any, fonte: str) -> dict[str, Any]:
    return {"chave": chave, "valor": valor, "fonte": fonte, "uso": "display_only"}


def _insights(lead: str, info: dict[str, str], metricas: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    low = lead.lower()
    rmf = info.get("região_metropolitana") or info.get("regiao_metropolitana") or ""
    if "região metropolitana" in low or "regiao metropolitana" in low or rmf:
        out.append(
            f"Município na Região Metropolitana de {rmf or 'Fortaleza'} segundo a Wikipédia (wikipedia)"
        )
    viz = info.get("vizinhos") or ""
    lim = next((m["valor"] for m in metricas if m.get("chave") == "limitrofes"), None)
    if viz:
        out.append(f"Limítrofes (infobox): {viz} (wikipedia)")
    elif lim:
        out.append(f"Limítrofes (Wikidata): {lim} (wikipedia)")
    if "fortaleza" in low or "rmf" in low:
        if not any("Metropolitana" in x for x in out):
            out.append("Integra a Região Metropolitana de Fortaleza (wikipedia)")
    return out[:4]


def _canonical_url(page: dict[str, Any], title: str) -> str:
    url = str(page.get("canonicalurl") or page.get("fullurl") or "").strip()
    if url:
        return url
    return f"https://pt.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"


def _fetch_live(cidade: str, uf: str, retrieved: str) -> dict[str, Any]:
    page = _resolve_page(cidade, uf)
    if _is_missing_page(page):
        return _empty_snapshot(cidade, uf, "missing", retrieved)
    assert page is not None
    title = str(page.get("title") or cidade)
    qid = str((page.get("pageprops") or {}).get("wikibase_item") or "")
    extract = str(page.get("extract") or "")
    lead = _lead_from_extract(extract)
    secoes = _split_sections(extract)
    info_raw = _parse_infobox(_wikitext(page))
    info_qual = {k: v for k, v in info_raw.items() if k in _INFOBOX_QUALITATIVE and v}
    metricas: list[dict[str, Any]] = []
    for raw_key, canon in _INFOBOX_METRIC.items():
        if raw_key in info_raw:
            metricas.append(_metrica(canon, info_raw[raw_key], f"wikipedia_infobox:{raw_key}"))

    label_ids: list[str] = []
    if qid:
        ents = _wd_entities([qid], "claims|labels|sitelinks")
        ent = ents.get(qid) or {}
        claims = ent.get("claims") or {}
        for pid, chave in _WD_CLAIM_KEYS.items():
            values = _pick_claims(claims, pid)
            if not values:
                continue
            if pid in {"P131", "P47"}:
                label_ids.extend(str(v) for v in values)
                metricas.append(_metrica(chave, values, f"wikidata:{pid}"))
            else:
                metricas.append(_metrica(chave, values[0] if len(values) == 1 else values, f"wikidata:{pid}"))
        if not qid:
            qid = str(ent.get("id") or qid)

    if label_ids:
        labs = _wd_entities(sorted(set(label_ids)), "labels")
        resolved = {
            i: str((e.get("labels") or {}).get("pt", {}).get("value") or i)
            for i, e in labs.items()
            if isinstance(e, dict)
        }
        for m in metricas:
            if m.get("chave") in {"localizado_em", "limitrofes"} and isinstance(m.get("valor"), list):
                m["valor"] = [resolved.get(str(v), v) for v in m["valor"]]

    # Dedupe metric keys: keep first (infobox) then wikidata extras with suffix
    seen: set[str] = set()
    uniq: list[dict[str, Any]] = []
    for m in metricas:
        key = str(m.get("chave"))
        fonte = str(m.get("fonte") or "")
        slot = key if key not in seen else f"{key}:{fonte}"
        if slot in seen and key in seen:
            continue
        seen.add(key)
        uniq.append(m)
    metricas = uniq

    lacunas: list[str] = []
    if not lead:
        lacunas.append("lead_vazio")
    if not secoes.get("economia"):
        lacunas.append("secao_economia")
    if not secoes.get("geografia"):
        lacunas.append("secao_geografia")

    snap: dict[str, Any] = {
        "status": "ok",
        "cidade": cidade,
        "uf": uf,
        "qid": qid,
        "url": _canonical_url(page, title),
        "title": title,
        "lead": lead,
        "infobox_qualitativo": info_qual,
        "secoes": secoes,
        "metricas_referencia": metricas,
        "insights_wiki": _insights(lead, info_qual, metricas),
        "fonte": "wikipedia_pt + wikidata",
        "retrieved_at": retrieved,
        "cache": {"hit": False, "path": ""},
        "lacunas": lacunas,
    }
    return snap
