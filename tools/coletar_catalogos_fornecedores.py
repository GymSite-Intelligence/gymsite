"""Coletor de catálogos de fornecedores de equipamentos de academia → RAG.

Busca (SearchAPI/Google), baixa os PDFs de catálogo dos principais fornecedores
de equipamentos fitness do Brasil e, opcionalmente, ingere no data store do
Vertex AI Search (gymsite-market-docs) para o Consultor consultar via
`consultar_base_conhecimento`.

Fluxo:
  1. Para cada fornecedor: SearchAPI engine=google com `q="{nome} catálogo
     equipamentos academia filetype:pdf"` → coleta links .pdf.
  2. Baixa cada PDF (httpx, valida content-type/tamanho), salva em --out.
  3. Escreve um manifest.json com o que achou/baixou.
  4. (--ingest) sobe os PDFs pra gs://{bucket}/catalogos/ e dispara
     import_documents (INCREMENTAL) no data store.

Uso:
  python -m tools.coletar_catalogos_fornecedores                 # busca + baixa
  python -m tools.coletar_catalogos_fornecedores --dry-run       # só lista URLs
  python -m tools.coletar_catalogos_fornecedores --ingest        # baixa + sobe + indexa
  python -m tools.coletar_catalogos_fornecedores --suppliers "Movement,Righetto"

Requer SEARCHAPI_KEY. Ingestão requer ADC com roles/discoveryengine.editor +
storage.objectAdmin no bucket.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import httpx

try:  # console Windows é cp1252 — o script imprime acento/→; força utf-8
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Fornecedores de equipamentos de academia no Brasil (semente — editável via --suppliers).
FORNECEDORES_PADRAO: list[str] = [
    "Movement",
    "Righetto Fitness",
    "Physicus",
    "Embreex",
    "Kikos Pro",
    "Life Fitness Brasil",
    "Technogym Brasil",
    "Matrix Fitness Brasil",
    "Sculptor equipamentos",
    "Gervasport",
    "Flex Equipment",
    "Taurus Fitness equipamentos",
]

_SEARCHAPI = "https://www.searchapi.io/api/v1/search"
_UA = "Mozilla/5.0 (compatible; GymSiteCatalogBot/1.0; +https://gymsite.com.br)"
_MAX_PDF_BYTES = 60 * 1024 * 1024  # 60 MB por catálogo

# Defaults do RAG (mesmos da tool de conhecimento — ver tools/discovery_engine_tools.py).
_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GOOGLE_PROJECT_ID") or "gen-lang-client-0106729343"
_LOCATION = os.environ.get("DISCOVERY_LOCATION", "global")
_DATASTORE = os.environ.get("DISCOVERY_DATASTORE_ID", "gymsite-market-docs_1782013477930")
_BUCKET = os.environ.get("CATALOGOS_BUCKET", "gymsite-market-docs-0106729343")


def _slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t or "doc"


def buscar_pdfs(fornecedor: str, n: int, key: str) -> list[dict]:
    """Retorna [{titulo, url}] de PDFs de catálogo do fornecedor via SearchAPI."""
    q = f'{fornecedor} catálogo equipamentos academia filetype:pdf'
    try:
        r = httpx.get(_SEARCHAPI, params={"engine": "google", "q": q, "api_key": key, "num": 10},
                      timeout=30.0)
        r.raise_for_status()
        organicos = r.json().get("organic_results") or []
    except Exception as e:
        print(f"  [busca] {fornecedor}: falhou — {type(e).__name__}: {e}")
        return []
    achados: list[dict] = []
    vistos: set[str] = set()
    for o in organicos:
        url = (o.get("link") or "").strip()
        if not url or url in vistos:
            continue
        if ".pdf" not in url.lower():
            continue  # confirma no download pelo content-type
        vistos.add(url)
        achados.append({"titulo": o.get("title") or fornecedor, "url": url})
        if len(achados) >= n:
            break
    return achados


def baixar_pdf(item: dict, fornecedor: str, out_dir: Path) -> dict:
    """Baixa um PDF validando content-type + tamanho. Retorna o item enriquecido."""
    url = item["url"]
    res = {**item, "fornecedor": fornecedor, "arquivo": None, "bytes": 0, "status": "erro"}
    try:
        with httpx.stream("GET", url, headers={"User-Agent": _UA}, follow_redirects=True,
                          timeout=60.0) as resp:
            resp.raise_for_status()
            ctype = resp.headers.get("content-type", "").lower()
            if "pdf" not in ctype and not url.lower().endswith(".pdf"):
                res["status"] = f"nao-pdf ({ctype})"
                return res
            conteudo = bytearray()
            for chunk in resp.iter_bytes():
                conteudo.extend(chunk)
                if len(conteudo) > _MAX_PDF_BYTES:
                    res["status"] = "grande-demais"
                    return res
        if not conteudo.startswith(b"%PDF"):
            res["status"] = "assinatura-invalida"
            return res
        # Nome por hash de CONTEÚDO (não da URL): a busca às vezes retorna o MESMO
        # PDF pra fornecedores diferentes (marca internacional sem catálogo BR) — assim
        # o duplicado colapsa no mesmo arquivo e não é reindexado.
        h = hashlib.sha1(bytes(conteudo)).hexdigest()[:12]
        nome = f"{h}.pdf"
        destino = out_dir / nome
        res["content_sha1"] = h
        if destino.exists():
            res.update({"arquivo": str(destino), "bytes": len(conteudo), "status": "duplicado"})
            print(f"  [dup] {fornecedor}: {nome} (mesmo conteúdo já baixado)")
            return res
        destino.write_bytes(bytes(conteudo))
        res.update({"arquivo": str(destino), "bytes": len(conteudo), "status": "ok"})
        print(f"  [ok] {fornecedor}: {nome} ({len(conteudo)//1024} KB)")
    except Exception as e:
        res["status"] = f"erro: {type(e).__name__}"
        print(f"  [falha] {fornecedor}: {url[:70]} — {type(e).__name__}")
    return res


def ingerir_no_rag(arquivos: list[str]) -> dict:
    """Sobe os PDFs pra gs://{bucket}/catalogos/ e dispara import_documents (INCREMENTAL)."""
    from google.cloud import discoveryengine_v1 as discoveryengine
    from google.cloud import storage

    if not arquivos:
        return {"status": "nada-pra-ingerir"}
    prefix = os.environ.get("CATALOGOS_PREFIX", "catalogos").strip("/")
    # 1. upload pro bucket
    sclient = storage.Client(project=_PROJECT)
    bucket = sclient.bucket(_BUCKET)
    uris: list[str] = []
    for f in arquivos:
        nome = Path(f).name
        blob = bucket.blob(f"{prefix}/{nome}")
        blob.upload_from_filename(f, content_type="application/pdf")
        uris.append(f"gs://{_BUCKET}/{prefix}/{nome}")
        print(f"  [gcs] subiu {nome}")
    # 2. import no data store (conteúdo não-estruturado via GCS)
    dclient = discoveryengine.DocumentServiceClient()
    parent = (f"projects/{_PROJECT}/locations/{_LOCATION}/collections/default_collection/"
              f"dataStores/{_DATASTORE}/branches/default_branch")
    req = discoveryengine.ImportDocumentsRequest(
        parent=parent,
        gcs_source=discoveryengine.GcsSource(input_uris=[f"gs://{_BUCKET}/{prefix}/*.pdf"],
                                             data_schema="content"),
        reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL,
    )
    op = dclient.import_documents(request=req)
    print(f"  [rag] import disparado: {op.operation.name}")
    return {"status": "import-disparado", "operation": op.operation.name, "uris": uris}


def main() -> int:
    ap = argparse.ArgumentParser(description="Coleta catálogos de fornecedores p/ o RAG.")
    ap.add_argument("--suppliers", help="Lista separada por vírgula (sobrescreve a semente).")
    ap.add_argument("--max-per-supplier", type=int, default=2, help="Máx. PDFs por fornecedor.")
    ap.add_argument("--out", default="data/catalogos_fornecedores", help="Diretório de saída.")
    ap.add_argument("--dry-run", action="store_true", help="Só busca/lista URLs, não baixa.")
    ap.add_argument("--ingest", action="store_true", help="Sobe pro bucket + importa no data store.")
    args = ap.parse_args()

    key = (os.environ.get("SEARCHAPI_KEY") or "").strip()
    if not key:
        print("ERRO: SEARCHAPI_KEY não configurada.", file=sys.stderr)
        return 2

    fornecedores = ([s.strip() for s in args.suppliers.split(",") if s.strip()]
                    if args.suppliers else FORNECEDORES_PADRAO)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Fornecedores: {len(fornecedores)} | out: {out_dir} | "
          f"{'DRY-RUN' if args.dry_run else 'baixando'}{' + INGEST' if args.ingest else ''}")

    manifest: list[dict] = []
    for forn in fornecedores:
        print(f"\n→ {forn}")
        achados = buscar_pdfs(forn, args.max_per_supplier, key)
        if not achados:
            print("  (nenhum PDF achado)")
            continue
        for item in achados:
            if args.dry_run:
                print(f"  [url] {item['url']}")
                manifest.append({**item, "fornecedor": forn, "status": "dry-run"})
            else:
                manifest.append(baixar_pdf(item, forn, out_dir))

    baixados = [m for m in manifest if m.get("status") == "ok"]
    (out_dir / "manifest.json").write_text(
        json.dumps({"gerado_em": datetime.now(timezone.utc).isoformat(),
                    "total_achados": len(manifest), "total_baixados": len(baixados),
                    "itens": manifest}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"\nResumo: {len(baixados)}/{len(manifest)} baixados → {out_dir/'manifest.json'}")

    if args.ingest and baixados:
        print("\n=== Ingestão no RAG ===")
        r = ingerir_no_rag([m["arquivo"] for m in baixados])
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif args.ingest:
        print("Nada baixado — ingestão pulada.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
