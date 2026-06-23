"""
Cria um Data Store + Engine (app de busca) no Vertex AI Search (Discovery Engine),
para conteúdo NÃO ESTRUTURADO (RAG sobre documentos). Idempotente: se já existir, segue.

Uso:
  python scripts/criar_store_rag.py \
      --datastore gymsite-obra-docs --engine gymsite-obra-app \
      --display "GymSite Obra (engenharia/projeto)"

Requer ADC ativo (`gcloud auth application-default login`) + IAM discoveryengine.admin/editor.
Depois de criar, rode o ingest:
  python scripts/ingerir_doc_rag.py CAMINHO --datastore gymsite-obra-docs --prefix obra
"""
from __future__ import annotations

import argparse
import os
import sys

_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GOOGLE_PROJECT_ID") or "gen-lang-client-0106729343"
_LOCATION = os.environ.get("DISCOVERY_LOCATION", "global")


def _parent() -> str:
    return f"projects/{_PROJECT}/locations/{_LOCATION}/collections/default_collection"


def criar_data_store(datastore_id: str, display: str) -> None:
    from google.cloud import discoveryengine_v1 as de
    from google.api_core.exceptions import AlreadyExists

    client = de.DataStoreServiceClient()
    ds = de.DataStore(
        display_name=display,
        industry_vertical=de.IndustryVertical.GENERIC,
        solution_types=[de.SolutionType.SOLUTION_TYPE_SEARCH],
        content_config=de.DataStore.ContentConfig.CONTENT_REQUIRED,  # não estruturado (docs)
    )
    try:
        op = client.create_data_store(parent=_parent(), data_store=ds, data_store_id=datastore_id)
        print(f"  [ds] criando '{datastore_id}'… (aguardando LRO)")
        op.result()
        print(f"  [ds] data store '{datastore_id}' criado.")
    except AlreadyExists:
        print(f"  [ds] data store '{datastore_id}' já existe — ok.")


def criar_engine(engine_id: str, datastore_id: str, display: str) -> None:
    from google.cloud import discoveryengine_v1 as de
    from google.api_core.exceptions import AlreadyExists

    client = de.EngineServiceClient()
    engine = de.Engine(
        display_name=display,
        industry_vertical=de.IndustryVertical.GENERIC,
        solution_type=de.SolutionType.SOLUTION_TYPE_SEARCH,
        data_store_ids=[datastore_id],
        search_engine_config=de.Engine.SearchEngineConfig(
            search_tier=de.SearchTier.SEARCH_TIER_ENTERPRISE,
        ),
    )
    try:
        op = client.create_engine(parent=_parent(), engine=engine, engine_id=engine_id)
        print(f"  [engine] criando '{engine_id}'… (aguardando LRO)")
        op.result()
        print(f"  [engine] engine/app '{engine_id}' criado, vinculado a '{datastore_id}'.")
    except AlreadyExists:
        print(f"  [engine] engine '{engine_id}' já existe — ok.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Cria data store + engine no Vertex AI Search.")
    ap.add_argument("--datastore", required=True, help="ID do data store (ex.: gymsite-obra-docs).")
    ap.add_argument("--engine", required=True, help="ID do engine/app (ex.: gymsite-obra-app).")
    ap.add_argument("--display", default="GymSite RAG", help="Nome de exibição.")
    args = ap.parse_args()
    print(f"Projeto {_PROJECT} | location {_LOCATION}")
    criar_data_store(args.datastore, args.display)
    criar_engine(args.engine, args.datastore, args.display)
    print("OK. Agora rode o ingest dos docs (--datastore", args.datastore, "--prefix obra).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
