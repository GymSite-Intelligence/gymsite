"""
scrape_confef_links.py — extrai os links oficiais do CONFEF e sobe um .txt por
link num bucket GCS, para virar base de conhecimento (RAG) regulatória do Consultor.

Uso:
    python scripts/scrape_confef_links.py            # scrape + upload
    python scripts/scrape_confef_links.py --dry-run  # só lista, não sobe

Env (defaults p/ o projeto GymSite):
    GOOGLE_CLOUD_PROJECT / GOOGLE_PROJECT_ID   projeto GCP
    CONFEF_BUCKET                              bucket de destino
    CONFEF_URL                                 página de origem

Auth = ADC (gcloud auth application-default login OU SA do runtime).

Integração depois do upload (RAG do Consultor): em vez de um data store isolado,
recomenda-se IMPORTAR estes .txt no data store de mercado já existente
(gymsite-market-docs), que é o que a tool `consultar_base_conhecimento` consulta —
assim o Consultor/Site Agent passam a citar os links do CONFEF sem nova fiação.
Ver tools/discovery_engine_tools.py + o fluxo import_documents.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

PROJECT_ID = (
    os.environ.get("GOOGLE_CLOUD_PROJECT")
    or os.environ.get("GOOGLE_PROJECT_ID")
    or "gen-lang-client-0106729343"
)
BUCKET_NAME = os.environ.get("CONFEF_BUCKET", "confef-links-data-0106729343")
URL_CONFEF = os.environ.get("CONFEF_URL", "https://www.confef.org.br/links/")

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GymSiteIntelligence/1.0)"}
_PREFIXO = "links"  # pasta dentro do bucket


def _slug(texto: str, fallback: str) -> str:
    """Nome de arquivo seguro a partir do texto do link."""
    s = texto.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)  # tira pontuação
    s = re.sub(r"[\s_-]+", "_", s).strip("_")
    s = s[:80]  # evita nomes gigantes
    return s or fallback


def extrair_links(html: str, base_url: str) -> list[dict[str, str]]:
    """Retorna [{nome, url}] de links http(s) únicos, deduplicados por URL."""
    soup = BeautifulSoup(html, "html.parser")
    vistos: set[str] = set()
    links: list[dict[str, str]] = []
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, str(a["href"]).strip())
        if urlparse(href).scheme not in ("http", "https"):
            continue
        if href in vistos:
            continue
        vistos.add(href)
        nome = a.get_text(strip=True) or "link_sem_nome"
        links.append({"nome": nome, "url": href})
    return links


def scraper_e_upload(dry_run: bool = False) -> int:
    print(f"Extraindo {URL_CONFEF} ...")
    resp = requests.get(URL_CONFEF, headers=_HEADERS, timeout=30)
    resp.raise_for_status()

    links = extrair_links(resp.text, URL_CONFEF)
    if not links:
        print("Nenhum link http(s) encontrado — verifique a estrutura da página.")
        return 0
    print(f"{len(links)} links únicos encontrados.")

    bucket = None
    if not dry_run:
        from google.cloud import storage  # import lazy: dry-run não exige a lib/credencial
        bucket = storage.Client(project=PROJECT_ID).bucket(BUCKET_NAME)

    usados: set[str] = set()
    n = 0
    for i, item in enumerate(links):
        slug = _slug(item["nome"], fallback=f"link_{i:03d}")
        # evita colisão de nomes (dois links com mesmo texto)
        nome_arq = slug
        k = 1
        while nome_arq in usados:
            nome_arq = f"{slug}_{k}"
            k += 1
        usados.add(nome_arq)

        file_name = f"{_PREFIXO}/{nome_arq}.txt"
        content = f"Nome: {item['nome']}\nURL: {item['url']}\nFonte: CONFEF (confef.org.br)\n"

        if dry_run or bucket is None:
            print(f"  [dry] {file_name}  ->  {item['url']}")
        else:
            bucket.blob(file_name).upload_from_string(content, content_type="text/plain")
            print(f"  [up] {file_name}")
        n += 1

    print(f"\nConcluído: {n} arquivos {'listados' if dry_run else f'enviados a gs://{BUCKET_NAME}/{_PREFIXO}/'}.")
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description="Scraper de links do CONFEF -> GCS (RAG).")
    ap.add_argument("--dry-run", action="store_true", help="lista sem subir ao bucket")
    args = ap.parse_args()
    try:
        scraper_e_upload(dry_run=args.dry_run)
    except requests.RequestException as e:
        print(f"Erro de rede ao buscar {URL_CONFEF}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
