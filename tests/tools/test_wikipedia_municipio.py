"""T1–T6 — carregar_wikipedia_municipio (A0 complementar, HTTP mocked)."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from tools.wikipedia_municipio import (
    BUNDLE_TICKET_FIELDS,
    apply_contexto_local_wiki,
    carregar_wikipedia_municipio,
    fetch_wikipedia_municipio,
    snapshot_to_markdown,
    wiki_slug,
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "wiki_itaitinga.json"


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _dispatch(url: str, params: dict, fixture: dict) -> dict:
    titles = str(params.get("titles") or params.get("page") or "").lower()
    ids = str(params.get("ids") or "")
    action = str(params.get("action") or "")
    props = str(params.get("props") or "")
    if "wikipedia.org" in url and action == "query":
        if "inexistente" in titles or "gymsitexyz" in titles or "cidadeinexistente" in titles:
            return fixture["query_missing"]
        return fixture["query_itaitinga"]
    if "wikidata.org" in url:
        if action == "wbsearchentities":
            q = str(params.get("search") or "").lower()
            if "inexistente" in q or "xyz" in q:
                return {"search": []}
            return {
                "search": [
                    {
                        "id": "Q2013483",
                        "label": "Itaitinga",
                        "description": "município do Ceará",
                    }
                ]
            }
        if action == "wbgetentities":
            if "Q2013483" in ids and "claims" in props:
                return fixture["wd_entity_q2013483"]
            return fixture["wd_labels"]
    raise AssertionError(f"unexpected wiki call url={url} params={params}")


@pytest.fixture
def wiki_http(monkeypatch):
    fixture = _fixture()
    calls: list[tuple[str, dict]] = []

    def _http(url: str, params: dict):
        calls.append((url, dict(params)))
        return _dispatch(url, params, fixture)

    monkeypatch.setattr("tools.wikipedia_municipio._http_json", _http)
    return calls


@pytest.fixture
def wiki_cache(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.wikipedia_municipio.CACHE_DIR", tmp_path)
    return tmp_path


def test_t1_itaitinga_ok(wiki_http, wiki_cache):
    md = carregar_wikipedia_municipio("Itaitinga", "CE")
    snap = fetch_wikipedia_municipio("Itaitinga", "CE")  # cache hit after first
    assert snap["status"] == "ok"
    assert snap["url"] == "https://pt.wikipedia.org/wiki/Itaitinga"
    assert snap["qid"] == "Q2013483"
    assert snap["lead"]
    assert "município" in snap["lead"].lower() or "Itaitinga" in snap["lead"]
    blob = json.dumps(snap, ensure_ascii=False).lower()
    assert "fortaleza" in blob or "metropolitana" in blob
    assert "pacatuba" in blob or "limítrof" in blob or "limitrof" in blob
    assert snap["metricas_referencia"]
    assert all(m.get("uso") == "display_only" for m in snap["metricas_referencia"])
    assert "status=ok" in md
    assert "https://pt.wikipedia.org/wiki/Itaitinga" in md
    assert "## Lead" in md
    assert "display_only" in md


def test_t2_wiki_ok_preserva_ticket_bundle():
    inner = {
        "ticket_medio_mercado": "R$ 119 (bundle)",
        "aluguel_medio_m2": "dados_nao_disponiveis",
        "renda_media_bairro": "dados_nao_disponiveis",
        "fonte": "market_bundle + CNPJ/CNO (tools)",
        "parque_ativo_total": 42,
    }
    snap = {
        "status": "ok",
        "url": "https://pt.wikipedia.org/wiki/Itaitinga",
        "qid": "Q2013483",
        "lead": "Itaitinga é um município…",
        "insights_wiki": ["RMF (wikipedia)"],
        "infobox_qualitativo": {"região_metropolitana": "Fortaleza"},
        "metricas_referencia": [
            {"chave": "populacao", "valor": "64648", "fonte": "wikidata:P1082", "uso": "display_only"}
        ],
        "fonte": "wikipedia_pt + wikidata",
        "retrieved_at": "2026-09-05T00:00:00+00:00",
    }
    changed = apply_contexto_local_wiki(inner, snap)
    assert changed is True
    assert inner["ticket_medio_mercado"] == "R$ 119 (bundle)"
    assert inner["aluguel_medio_m2"] == "dados_nao_disponiveis"
    assert inner["renda_media_bairro"] == "dados_nao_disponiveis"
    assert inner["parque_ativo_total"] == 42
    assert inner["contexto_local_wiki"]["status"] == "ok"
    assert "wikipedia" in inner["fonte"]
    for key in BUNDLE_TICKET_FIELDS:
        assert key not in inner["contexto_local_wiki"]


def test_t3_cidade_inexistente_missing(wiki_http, wiki_cache):
    md = carregar_wikipedia_municipio("CidadeInexistenteGymSiteXYZ", "CE")
    snap = fetch_wikipedia_municipio("CidadeInexistenteGymSiteXYZ", "CE")
    assert snap["status"] == "missing"
    assert "status=missing" in md
    assert snap["qid"] == ""
    assert isinstance(md, str)


def test_t4_timeout_error(monkeypatch, wiki_cache):
    def _boom(url, params):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr("tools.wikipedia_municipio._http_json", _boom)
    md = carregar_wikipedia_municipio("Itaitinga", "CE")
    snap = fetch_wikipedia_municipio("Itaitinga", "CE")
    assert snap["status"] == "error"
    assert "status=error" in md
    assert isinstance(md, str)


def test_t5_cache_hit_sem_http(wiki_http, wiki_cache):
    first = fetch_wikipedia_municipio("Itaitinga", "CE")
    assert first["status"] == "ok"
    assert first["cache"]["hit"] is False
    n_first = len(wiki_http)
    assert n_first >= 1
    wiki_http.clear()
    second = fetch_wikipedia_municipio("Itaitinga", "CE")
    assert second["status"] == "ok"
    assert second["cache"]["hit"] is True
    assert wiki_http == []
    md = carregar_wikipedia_municipio("Itaitinga", "CE")
    assert "status=ok" in md
    assert wiki_http == []


def test_t6_wiki_nunca_preenche_parque_score(monkeypatch):
    import agents.a0_context_builder as a0
    from tools.test_a0_override import _FAKE_TOOL, _ctx, _mc_llm

    wiki_pop = "64648"
    wiki_snap = {
        "status": "ok",
        "url": "https://pt.wikipedia.org/wiki/Itaitinga",
        "qid": "Q2013483",
        "lead": "lead",
        "insights_wiki": [],
        "infobox_qualitativo": {},
        "metricas_referencia": [
            {"chave": "populacao", "valor": wiki_pop, "fonte": "wikidata:P1082", "uso": "display_only"},
            {"chave": "idh", "valor": "0.626", "fonte": "wikipedia_infobox:idh", "uso": "display_only"},
        ],
        "fonte": "wikipedia_pt + wikidata",
        "retrieved_at": "2026-09-05T00:00:00+00:00",
    }

    def _no_live(*_a, **_k):
        raise AssertionError("override must not refetch wiki when snapshot exists")

    monkeypatch.setattr("tools.cnpj_fitness_tools.dados_parque_cnpj_para_a0", lambda *a, **k: _FAKE_TOOL)
    monkeypatch.setattr("tools.wikipedia_municipio.fetch_wikipedia_municipio", _no_live)
    monkeypatch.setattr("agents.a0_context_builder.fetch_wikipedia_municipio", _no_live)

    st = _mc_llm({"parque_ativo_total": 9999})
    st["a0_tool_snapshots"] = {"carregar_wikipedia_municipio": wiki_snap}
    a0._a0_override_cnpj_numeros(_ctx(st))
    inner = st["market_context"]["market_context"]
    assert inner["parque_ativo_total"] == 1828
    assert inner["parque_ativo_total"] != int(wiki_pop)
    assert inner["parque_comercial_total"] == 1158
    assert not any(
        k.startswith("score_") and str(inner.get(k)) == wiki_pop for k in inner
    )
    assert inner["contexto_local_wiki"]["status"] == "ok"
    assert all(
        m.get("uso") == "display_only"
        for m in inner["contexto_local_wiki"]["metricas_referencia"]
    )
    assert inner["contexto_local_wiki"]["metricas_referencia"][0]["valor"] == wiki_pop


def test_a0_tem_exatamente_quatro_tools():
    import agents.a0_context_builder as a0

    names: set[str] = set()
    for t in getattr(a0.context_builder_agent, "tools", None) or []:
        name = getattr(t, "__name__", None) or getattr(t, "name", None)
        if not name:
            fn = getattr(t, "func", None)
            name = getattr(fn, "__name__", None) if fn is not None else None
        names.add(str(name or t))
    assert names == {
        "carregar_market_bundle",
        "carregar_wikipedia_municipio",
        "dados_parque_cnpj_para_a0",
        "fatos_competicao_local",
    }
    inst = a0.context_builder_agent.instruction or ""
    assert "carregar_wikipedia_municipio" in inst
    assert "SEMPRE" in inst
    assert "somente estas quatro" in inst


def test_after_tool_persiste_snapshot_wiki_sem_slim(wiki_http, wiki_cache):
    from agents.a0_context_builder import _a0_after_tool_slim

    md = carregar_wikipedia_municipio("Itaitinga", "CE")
    st: dict = {}
    tool = SimpleNamespace(name="carregar_wikipedia_municipio")
    out = _a0_after_tool_slim(tool, {"cidade": "Itaitinga", "uf": "CE"}, SimpleNamespace(state=st), md)
    assert out is None
    snap = st["a0_tool_snapshots"]["carregar_wikipedia_municipio"]
    assert snap["status"] == "ok"
    assert snap["lead"]
    assert snap["metricas_referencia"]


def test_slug_sem_bairro():
    assert wiki_slug("Itaitinga", "ce") == "itaitinga_CE"


def test_smoke_markdown_from_snapshot():
    snap = {
        "status": "ok",
        "cidade": "Itaitinga",
        "uf": "CE",
        "qid": "Q2013483",
        "url": "https://pt.wikipedia.org/wiki/Itaitinga",
        "title": "Itaitinga",
        "lead": "Itaitinga é um município da RMF.",
        "infobox_qualitativo": {"região_metropolitana": "Fortaleza"},
        "secoes": {"economia": "Mineração.", "geografia": "Tabuleiros."},
        "metricas_referencia": [
            {"chave": "populacao", "valor": "64648", "fonte": "wikidata:P1082", "uso": "display_only"}
        ],
        "retrieved_at": "2026-09-05T00:00:00+00:00",
    }
    md = snapshot_to_markdown(snap)
    assert md.startswith("<!-- wikipedia_municipio status=ok")
    assert "qid=Q2013483" in md
    assert "## Economia" in md
