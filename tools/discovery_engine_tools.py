"""Base de conhecimento qualitativa via Vertex AI Search (Discovery Engine).

RAG sobre os documentos importados no app `gymsite-market-app` (Agent Builder).
Camada QUALITATIVA do Consultor V2 — metodologia, regulatório/zoneamento/licença,
franquia/operação e pesquisa de mercado setorial. NÃO produz número: os números de
viabilidade vêm das tools determinísticas (A0–A4). Aqui o consumidor recebe trechos
+ citações e SINTETIZA por conta própria (sem SummarySpec do Google).

Alvo é o ENGINE do Agent Builder (engines novos usam serving config `default_search`),
não o dataStore — tudo env-driven com defaults. Auth via ADC (em prod, o SA do
Cloud Run precisa de roles/discoveryengine.viewer).
"""
import os

from google.api_core.client_options import ClientOptions

_DEFAULT_ENGINE = "gymsite-market-app_1782013373452"
_DEFAULT_SERVING = "default_search"
_FONTE = "Vertex AI Search (gymsite-market-app)"


def _config() -> tuple[str, str, str, str]:
    """(project, location, engine_id, serving_config) — env com defaults."""
    project = (os.environ.get("GOOGLE_CLOUD_PROJECT")
               or os.environ.get("GOOGLE_PROJECT_ID")
               or "gen-lang-client-0106729343")
    location = os.environ.get("DISCOVERY_LOCATION", "global")
    engine = os.environ.get("DISCOVERY_ENGINE_ID", _DEFAULT_ENGINE)
    serving = os.environ.get("DISCOVERY_SERVING_CONFIG", _DEFAULT_SERVING)
    return project, location, engine, serving


def buscar_conhecimento(pergunta: str, n: int = 4) -> dict:
    """Busca trechos relevantes no app de conhecimento e devolve ESTRUTURADO.

    Returns:
        {"resultados": [{"titulo","uri","trecho"}], "n_docs": int, "fonte": str}
        + "erro" quando degrada (sem quebrar o caller).
    """
    from google.cloud import discoveryengine_v1 as discoveryengine

    if not (pergunta or "").strip():
        return {"resultados": [], "n_docs": 0, "fonte": _FONTE, "erro": "pergunta vazia"}

    project, location, engine, serving = _config()
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
                trecho = extractive[0].get("content", "")
            else:
                snippets = d.get("snippets") or []
                if snippets:
                    trecho = snippets[0].get("snippet", "")
            if trecho:
                resultados.append({"titulo": titulo, "uri": uri, "trecho": trecho})

        return {"resultados": resultados, "n_docs": len(resultados), "fonte": _FONTE}
    except Exception as e:
        return {"resultados": [], "n_docs": 0, "fonte": _FONTE,
                "erro": f"{type(e).__name__}: {e}"}


def search_market_docs(query: str, project_id: str = None, location: str = "global",
                       search_engine_id: str = None) -> str:
    """Compat: versão string (legada). Delega a buscar_conhecimento."""
    r = buscar_conhecimento(query)
    if r.get("erro"):
        return f"Erro ao consultar o Vertex AI Agent Builder: {r['erro']}"
    if not r["resultados"]:
        return "Nenhuma informação relevante encontrada nos documentos de mercado."
    return "\n\n".join(f"Fonte [{x['uri'] or x['titulo']}]: {x['trecho']}" for x in r["resultados"])


if __name__ == "__main__":
    import json
    print(json.dumps(buscar_conhecimento("Tendência do mercado de academias"),
                     ensure_ascii=False, indent=2))
