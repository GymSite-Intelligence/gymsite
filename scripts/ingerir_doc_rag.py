"""
Ingere UM documento (txt/pdf) num data store do Vertex AI Search (Discovery Engine).
Sobe pro GCS e dispara import_documents INCREMENTAL (data_schema="content").

Uso:
  python scripts/ingerir_doc_rag.py CAMINHO_DO_ARQUIVO \
      [--datastore gymsite-equip-docs] [--prefix engenharia] [--bucket gymsite-market-docs-0106729343]

Requer ADC ativo (`gcloud auth application-default login`) + IAM:
  discoveryengine.editor (import) e storage.objectAdmin no bucket.
"""
from __future__ import annotations

import argparse
import mimetypes
import os
import sys
from pathlib import Path

_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GOOGLE_PROJECT_ID") or "gen-lang-client-0106729343"
_LOCATION = os.environ.get("DISCOVERY_LOCATION", "global")
_DEFAULT_BUCKET = "gymsite-market-docs-0106729343"
_DEFAULT_DATASTORE = "gymsite-equip-docs"


def ingerir(arquivo: str, datastore: str, prefix: str, bucket: str) -> dict:
    from google.cloud import discoveryengine_v1 as discoveryengine
    from google.cloud import storage

    p = Path(arquivo)
    if not p.is_file():
        raise SystemExit(f"Arquivo não encontrado: {arquivo}")
    prefix = prefix.strip("/")
    ctype = mimetypes.guess_type(p.name)[0] or "text/plain"

    # 1. upload pro bucket
    sclient = storage.Client(project=_PROJECT)
    blob = sclient.bucket(bucket).blob(f"{prefix}/{p.name}")
    blob.upload_from_filename(str(p), content_type=ctype)
    uri = f"gs://{bucket}/{prefix}/{p.name}"
    print(f"  [gcs] subiu {p.name} → {uri} ({ctype})")

    # 2. import INCREMENTAL no data store (conteúdo não-estruturado)
    dclient = discoveryengine.DocumentServiceClient()
    parent = (f"projects/{_PROJECT}/locations/{_LOCATION}/collections/default_collection/"
              f"dataStores/{datastore}/branches/default_branch")
    req = discoveryengine.ImportDocumentsRequest(
        parent=parent,
        gcs_source=discoveryengine.GcsSource(input_uris=[uri], data_schema="content"),
        reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL,
    )
    op = dclient.import_documents(request=req)
    print(f"  [rag] import disparado em '{datastore}': {op.operation.name}")
    return {"status": "import-disparado", "operation": op.operation.name, "uri": uri}


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingere um doc num data store do Vertex AI Search.")
    ap.add_argument("arquivo", help="Caminho do arquivo (txt/pdf).")
    ap.add_argument("--datastore", default=_DEFAULT_DATASTORE, help=f"ID do data store (default {_DEFAULT_DATASTORE}).")
    ap.add_argument("--prefix", default="engenharia", help="Prefixo (pasta) no bucket.")
    ap.add_argument("--bucket", default=_DEFAULT_BUCKET, help=f"Bucket GCS (default {_DEFAULT_BUCKET}).")
    args = ap.parse_args()
    res = ingerir(args.arquivo, args.datastore, args.prefix, args.bucket)
    print(res)
    return 0


if __name__ == "__main__":
    sys.exit(main())
