"""Base de conhecimento qualitativa — Vertex AI Search DEPRECATED.

Por padrão NÃO chama Discovery Engine (billing Vertex off). Opt-in:
  VERTEX_RAG_ENABLED=1

Caminho novo: Eros RAG / kb_rag via tools em agents_site (consultar_base_mercado
e consultar_eros_*). Este módulo só sobrevive como legado opt-in.
"""
import os
import re

from google.api_core.client_options import ClientOptions

_DEFAULT_ENGINE = "gymsite-market-app_1782013373452"
_DEFAULT_EQUIP_ENGINE = "gymsite-equip-app"  # engine só de catálogos de equipamento
_DEFAULT_CONSULTOR_ENGINE = "gymsite-consultor-app"  # BI/estratégia INTERNO — só consultor logado, NUNCA degustação
_DEFAULT_SERVING = "default_search"
_FONTE = "Vertex AI Search (gymsite-market-app)"
_FONTE_DEPRECATED = "RAG (Vertex descontinuado — use Eros)"

_MSG_STUB = (
    "A base qualitativa Vertex AI Search está descontinuada neste ambiente. "
    "Para concorrência e saturação, use os números de buscar_concorrentes. "
    "Metodologia/benchmarks: aguardando RAG Eros (EROS_GROUP_ID_MERCADO)."
)

_BILLING_RE = re.compile(
    r"billing|faturamento|dunning|PERMISSION_DENIED|not enabled|has not been used",
    re.I,
)


def vertex_rag_enabled() -> bool:
    """Default off — Vertex Discovery deprecated."""
    return (os.getenv("VERTEX_RAG_ENABLED") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _stub_vertex(pergunta: str = "") -> dict:
    return {
        "resultados": [],
        "n_docs": 0,
        "fonte": _FONTE_DEPRECATED,
        "status": "deprecated",
        "aviso_usuario": _MSG_STUB,
        "erro": None,
        "pergunta": (pergunta or "").strip()[:200],
    }


def _sanitize_erro(exc: BaseException) -> str:
    msg = f"{type(exc).__name__}: {exc}"
    if _BILLING_RE.search(msg):
        return (
            "vertex_billing_off: Discovery Engine indisponível (faturamento GCP). "
            "Vertex RAG descontinuado — use Eros / buscar_concorrentes."
        )
    return msg


def _config(engine_id: str | None = None, serving_config: str | None = None) -> tuple[str, str, str, str]:
    """(project, location, engine_id, serving_config) — args > env > defaults."""
    project = (os.environ.get("GOOGLE_CLOUD_PROJECT")
               or os.environ.get("GOOGLE_PROJECT_ID")
               or "gen-lang-client-0106729343")
    location = os.environ.get("DISCOVERY_LOCATION", "global")
    engine = engine_id or os.environ.get("DISCOVERY_ENGINE_ID", _DEFAULT_ENGINE)
    serving = serving_config or os.environ.get("DISCOVERY_SERVING_CONFIG", _DEFAULT_SERVING)
    return project, location, engine, serving


def buscar_conhecimento(pergunta: str, n: int = 4,
                        engine_id: str | None = None,
                        serving_config: str | None = None) -> dict:
    """Busca trechos no app Vertex — só se VERTEX_RAG_ENABLED=1; senão stub limpo.

    Returns:
        {"resultados": [{"titulo","uri","trecho"}], "n_docs": int, "fonte": str}
        + "erro" / "status" quando degrada (sem quebrar o caller).
    """
    if not vertex_rag_enabled():
        return _stub_vertex(pergunta)

    from google.cloud import discoveryengine_v1 as discoveryengine

    if not (pergunta or "").strip():
        return {"resultados": [], "n_docs": 0, "fonte": _FONTE, "erro": "pergunta vazia"}

    project, location, engine, serving = _config(engine_id, serving_config)
    client_options = (
        ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
        if location != "global" else None
    )
    try:
        client = discoveryengine.SearchServiceClient(client_options=client_options)
        # Engine path (não dataStore) — engines do Agent Builder novos.
        serving_config = (
            f"projects/{project}/locations/{location}/collections/default_collection/"
            f"engines/{engine}/servingConfigs/{serving}"
        )
        spec = discoveryengine.SearchRequest.ContentSearchSpec(
            snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                return_snippet=True,
            ),
            extractive_content_spec=discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
                max_extractive_answer_count=1,
            ),
        )
        request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query=pergunta,
            page_size=max(1, min(int(n or 4), 10)),
            content_search_spec=spec,
        )
        response = client.search(request)

        resultados: list[dict] = []
        for result in response.results:
            d = result.document.derived_struct_data or {}
            titulo = d.get("title") or d.get("link") or "Documento"
            uri = d.get("link", "")
            trecho = ""
            extractive = d.get("extractive_answers") or []
            if extractive:
                trecho = (extractive[0].get("content") or "").strip()
            if not trecho:
                # Snippet só vale com status SUCCESS — o Discovery Engine devolve
                # "No snippet is available for this page." (placeholder) enquanto
                # indexa; nunca repassar isso como conteúdo.
                for sn in (d.get("snippets") or []):
                    status = sn.get("snippet_status")
                    cand = (sn.get("snippet") or "").strip()
                    if cand and status != "NO_SNIPPET_AVAILABLE" and "No snippet is available" not in cand:
                        trecho = cand
                        break
            if trecho:
                resultados.append({"titulo": titulo, "uri": uri, "trecho": trecho})

        return {"resultados": resultados, "n_docs": len(resultados), "fonte": _FONTE}
    except Exception as e:
        return {
            "resultados": [],
            "n_docs": 0,
            "fonte": _FONTE_DEPRECATED,
            "status": "indisponivel",
            "aviso_usuario": _MSG_STUB,
            "erro": _sanitize_erro(e),
        }


def buscar_catalogos_equipamentos(pergunta: str, n: int = 4) -> dict:
    """Busca nos CATÁLOGOS de fornecedores de equipamento (data store/engine separado
    `gymsite-equip-docs`/`gymsite-equip-app`). Mesmo formato de buscar_conhecimento."""
    engine = os.environ.get("DISCOVERY_EQUIP_ENGINE_ID", _DEFAULT_EQUIP_ENGINE)
    r = buscar_conhecimento(pergunta, n=n, engine_id=engine)
    if r.get("status") not in ("deprecated", "indisponivel"):
        r["fonte"] = "Vertex AI Search (catálogos de equipamento)"
    return r


def buscar_conhecimento_consultor(pergunta: str, n: int = 4) -> dict:
    """Busca na base INTERNA de BI/estratégia (`gymsite-consultor-docs`/`gymsite-consultor-app`).
    Conteúdo sensível (posicionamento próprio, pricing, análise competitiva) — só o consultor
    LOGADO pode consultar. NUNCA exposto à degustação pública (barreira anti-vazamento no engine)."""
    engine = os.environ.get("DISCOVERY_CONSULTOR_ENGINE_ID", _DEFAULT_CONSULTOR_ENGINE)
    r = buscar_conhecimento(pergunta, n=n, engine_id=engine)
    if r.get("status") not in ("deprecated", "indisponivel"):
        r["fonte"] = "Vertex AI Search (consultor interno)"
    return r


def search_market_docs(query: str, project_id: str = None, location: str = "global",
                       search_engine_id: str = None) -> str:
    """Compat: versão string (legada). Delega a buscar_conhecimento."""
    r = buscar_conhecimento(query)
    if r.get("status") in ("deprecated", "indisponivel"):
        return r.get("aviso_usuario") or _MSG_STUB
    if r.get("erro"):
        return f"Erro ao consultar a base de conhecimento: {r['erro']}"
    if not r["resultados"]:
        return "Nenhuma informação relevante encontrada nos documentos de mercado."
    return "\n\n".join(f"Fonte [{x['uri'] or x['titulo']}]: {x['trecho']}" for x in r["resultados"])


if __name__ == "__main__":
    import json
    print(json.dumps(buscar_conhecimento("Tendência do mercado de academias"),
                     ensure_ascii=False, indent=2))
