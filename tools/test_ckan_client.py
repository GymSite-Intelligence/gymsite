"""Testes CKAN client (mock, sem rede)."""
from __future__ import annotations

import pytest

from tools.ckan_client import (
    CkanApiError,
    ckan_action,
    extract_cgu_extras,
    fq_cobertura,
    fq_group,
    package_search,
    search_datasets_for_city,
    search_datasets_macro,
    summarize_package,
)


def _mock_client(resp):
    """Client fake cobrindo GET (ações de leitura) e POST (demais)."""
    handler = type(
        "H",
        (),
        {
            "get": lambda *a, **k: resp,
            "post": lambda *a, **k: resp,
        },
    )()
    return type(
        "C",
        (),
        {
            "__enter__": lambda s: handler,
            "__exit__": lambda *a: None,
        },
    )()


def test_ckan_action_success(monkeypatch):
    class Resp:
        status_code = 200

        def json(self):
            return {"success": True, "result": {"count": 0, "results": []}}

    monkeypatch.setattr("tools.ckan_client.httpx.Client", lambda **kw: _mock_client(Resp()))
    r = ckan_action("status_show", portal_base="https://example.com")
    assert r == {"count": 0, "results": []}


def test_ckan_action_failure(monkeypatch):
    class Resp:
        status_code = 200

        def json(self):
            return {"success": False, "error": {"message": "not found"}}

    monkeypatch.setattr("tools.ckan_client.httpx.Client", lambda **kw: _mock_client(Resp()))
    with pytest.raises(CkanApiError):
        ckan_action("package_show", {"id": "x"}, portal_base="https://example.com")


def test_search_datasets_for_city_dedup(monkeypatch):
    def fake_search(q, **kwargs):
        return {"results": [{"id": "a", "name": "a", "title": "T", "organization": {}}]}

    monkeypatch.setattr("tools.ckan_client.package_search", fake_search)
    out = search_datasets_for_city("Fortaleza", "CE")
    assert len(out) >= 1
    assert out[0]["id"] == "a"


def test_package_search_fq_list(monkeypatch):
    captured = {}

    def fake_action(action, params=None, **kwargs):
        captured["params"] = params
        return {"count": 0, "results": []}

    monkeypatch.setattr("tools.ckan_client.ckan_action", fake_action)
    package_search("*:*", fq=['groups:"Habitação"', "extras_coberturaEspacial:FEDERAL"])
    assert captured["params"]["fq"] == [
        'groups:"Habitação"',
        "extras_coberturaEspacial:FEDERAL",
    ]


def test_fq_helpers():
    assert fq_group("Habitação") == 'groups:"Habitação"'
    assert fq_cobertura("FEDERAL") == ["extras_coberturaEspacial:FEDERAL"]
    assert fq_cobertura("ESTADUAL", valor="DF") == [
        "extras_coberturaEspacial:ESTADUAL",
        "extras_valorCoberturaEspacial:DF",
    ]


def test_extract_cgu_extras_and_summarize():
    pkg = {
        "id": "1",
        "name": "x",
        "title": "T",
        "organization": {"title": "Org"},
        "groups": [{"display_name": "Habitação"}],
        "extras": [
            {"key": "coberturaEspacial", "value": "MUNICIPAL"},
            {"key": "valorCoberturaEspacial", "value": "230440"},
            {"key": "descontinuado", "value": "false"},
            {"key": "ignore_me", "value": "x"},
        ],
    }
    extras = extract_cgu_extras(pkg)
    assert extras["coberturaEspacial"] == "MUNICIPAL"
    assert "ignore_me" not in extras
    summ = summarize_package(pkg, portal="https://dados.gov.br")
    assert summ["join_ibge6"] == "230440"
    assert summ["groups"] == ["Habitação"]
    assert summ["discontinued"] is False


def test_search_datasets_macro_action_municipal(monkeypatch):
    """Macro em portal não-federal ainda usa Action package_search."""

    def fake_search(q, **kwargs):
        return {
            "results": [
                {
                    "id": "h1",
                    "name": "hab",
                    "title": "Hab",
                    "organization": {},
                    "extras": [{"key": "descontinuado", "value": "true"}],
                },
                {
                    "id": "h2",
                    "name": "hab2",
                    "title": "Hab2",
                    "organization": {},
                    "extras": [],
                },
            ]
        }

    def fake_show(pid, **kwargs):
        if pid == "h1":
            return {
                "id": "h1",
                "title": "Hab",
                "organization": {},
                "extras": [{"key": "descontinuado", "value": "true"}],
                "groups": [],
            }
        return {
            "id": "h2",
            "title": "Hab2",
            "organization": {},
            "extras": [{"key": "coberturaEspacial", "value": "FEDERAL"}],
            "groups": [{"title": "Habitação"}],
        }

    monkeypatch.setattr("tools.ckan_client.package_search", fake_search)
    monkeypatch.setattr("tools.ckan_client.package_show", fake_show)
    monkeypatch.setenv("CKAN_API_KEY", "test-key")
    out = search_datasets_macro(
        groups=["Habitação"],
        portal_base="https://dados.fortaleza.ce.gov.br",
    )
    ids = {x["id"] for x in out}
    assert "h1" not in ids  # discontinued skipped
    assert "h2" in ids
    assert out[0]["matched_group"] == "Habitação"


def test_summarize_conjunto_publico():
    from tools.ckan_client import summarize_conjunto_publico

    detail = {
        "id": "abc",
        "nome": "censo-x",
        "titulo": "Censo X",
        "organizacao": "ibge",
        "temas": [{"name": "habitacao", "title": "Habitação"}],
        "coberturaEspacial": "ESTADUAL",
        "valorCoberturaEspacial": "DF",
        "descontinuado": False,
        "recursos": [{"id": "r1"}],
    }
    summ = summarize_conjunto_publico(detail)
    assert summ["id"] == "abc"
    assert summ["groups"] == ["Habitação"]
    assert summ["join_uf"] == "DF"
    assert summ["api"] == "publico"
    assert summ["n_recursos"] == 1


def test_search_datasets_macro_federal_uses_org_seed(monkeypatch):
    from tools.ckan_client import search_datasets_macro

    called = {}

    def fake_org_seed(**kwargs):
        called.update(kwargs)
        return [{"id": "x", "title": "T", "matched_group": "Habitação"}]

    monkeypatch.setattr("tools.ckan_client.search_datasets_org_seed", fake_org_seed)
    monkeypatch.setenv("CKAN_API_KEY", "test-key")
    out = search_datasets_macro(
        groups=["Habitação"],
        portal_base="https://dados.gov.br",
        org_slugs=["ministerio-das-cidades"],
    )
    assert out[0]["id"] == "x"
    assert called["org_slugs"] == ["ministerio-das-cidades"]
    assert called["groups"] == ["Habitação"]


def test_resolve_org_seed_aliases():
    from tools.ckan_client import ORG_SEED, resolve_org_seed

    pairs = resolve_org_seed(["ministerio-das-cidades", "ipea"])
    assert pairs[0][0] == "ministerio-das-cidades"
    assert pairs[0][1] == ORG_SEED["ministerio-das-cidades"]["id"]
    assert len(resolve_org_seed()) >= 5
    fazenda = dict(resolve_org_seed(["ministerio-da-fazenda"]))
    assert fazenda["ministerio-da-fazenda"] == ORG_SEED["ministerio-da-fazenda"]["id"]
    anvisa = dict(resolve_org_seed(["agencia-nacional-de-vigilancia-sanitaria-anvisa"]))
    assert anvisa["agencia-nacional-de-vigilancia-sanitaria-anvisa"] == (
        ORG_SEED["agencia-nacional-de-vigilancia-sanitaria-anvisa"]["id"]
    )
    esporte = dict(resolve_org_seed(["ministerio-do-esporte"]))
    assert esporte["ministerio-do-esporte"] == ORG_SEED["ministerio-do-esporte"]["id"]


def test_search_datasets_org_seed_mock(monkeypatch):
    from tools.ckan_client import search_datasets_org_seed

    monkeypatch.setenv("CKAN_API_KEY", "test-key")

    def fake_list(*, pagina=1, id_organizacao=None, nome_conjunto=None, **kwargs):
        if id_organizacao and pagina == 1:
            return [
                {"id": "d1", "nome": "hab-1", "titulo": "Hab 1"},
                {"id": "d2", "nome": "skip", "titulo": "Skip"},
            ]
        return []

    def fake_get(pid):
        if pid == "d1":
            return {
                "id": "d1",
                "nome": "hab-1",
                "titulo": "Habitação Nacional",
                "organizacao": "mcid",
                "temas": [{"title": "Habitação"}],
                "coberturaEspacial": "FEDERAL",
                "descontinuado": False,
                "recursos": [],
            }
        return {
            "id": "d2",
            "nome": "skip",
            "titulo": "Outro",
            "organizacao": "x",
            "temas": [{"title": "Saúde"}],
            "descontinuado": False,
            "recursos": [],
        }

    monkeypatch.setattr("tools.ckan_client.list_conjuntos_dados", fake_list)
    monkeypatch.setattr("tools.ckan_client.get_conjunto_dados", fake_get)
    out = search_datasets_org_seed(
        org_slugs=["ministerio-das-cidades"],
        nome_queries=[],
        groups=["Habitação"],
        require_group_match=True,
        max_pages_per_org=1,
    )
    assert len(out) == 1
    assert out[0]["id"] == "d1"
    assert out[0]["matched_group"] == "Habitação"
