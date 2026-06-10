"""
tools/rfb_cnpj_fitness_loader.py

Loader mínimo do CNPJ Aberto (RFB) para identificar estabelecimentos fitness
(CNAE 9313100) por município/UF/cidade e gravar no Supabase.

Fonte: https://dadosabertos.rfb.gov.br/CNPJ/dados_abertos_cnpj/YYYY-MM/
Arquivos: Estabelecimentos0.zip..Estabelecimentos9.zip, Municipios.zip

Uso (exemplos):
  python tools/rfb_cnpj_fitness_loader.py --ref 2026-05 --cidade Fortaleza --uf CE --dry-run
  python tools/rfb_cnpj_fitness_loader.py --ref 2026-05 --nacional --rfb-share-token TOKEN
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import re
import sys
import zipfile
import time
from datetime import date
from pathlib import Path
from typing import Any, Iterable
import base64
import httpx
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.cnpj_segment_classifier import classificar_segmento
_ENV_CANDIDATES = (
    _ROOT / ".env",
    _ROOT / "frontend" / ".env",
    _ROOT / "db" / ".env",
    _ROOT / "gymsite_intelligence" / ".env",
)


def _bootstrap_env() -> list[Path]:
    """Carrega .env do repo (independente do cwd do PowerShell)."""
    loaded: list[Path] = []
    for path in _ENV_CANDIDATES:
        if path.is_file() and load_dotenv(path, override=False):
            loaded.append(path)
    # Frontend costuma ter só VITE_* — reutiliza URL se faltar SUPABASE_URL
    if not (os.getenv("SUPABASE_URL") or "").strip():
        vite_url = (os.getenv("VITE_SUPABASE_URL") or "").strip()
        if vite_url:
            os.environ["SUPABASE_URL"] = vite_url
    return loaded


_BOOTSTRAPPED = _bootstrap_env()

BASE_URL = "https://dadosabertos.rfb.gov.br/CNPJ/dados_abertos_cnpj"
DEFAULT_WEBDAV_BASE = "https://arquivos.receitafederal.gov.br/public.php/webdav"
CNAE_ALVO = "9313100"
SITUACAO_ATIVA = {"2", "02"}  # layout usa 2, mas tolera 02

# Layout Estabelecimentos (30 colunas) — docs/cnpj-metadados.pdf
EST_CNPJ_BASICO = 0
EST_CNPJ_ORDEM = 1
EST_CNPJ_DV = 2
EST_NOME_FANTASIA = 4
EST_SITUACAO = 5
EST_DATA_SITUACAO = 6
EST_DATA_INICIO = 10
EST_CNAE_PRINCIPAL = 11
EST_CNAE_SECUNDARIA = 12
EST_TIPO_LOGRADOURO = 13
EST_LOGRADOURO = 14
EST_NUMERO = 15
EST_COMPLEMENTO = 16
EST_BAIRRO = 17
EST_CEP = 18
EST_UF = 19
EST_MUNICIPIO = 20
EST_DDD1 = 21
EST_TELEFONE1 = 22
EST_EMAIL = 27

# Layout Empresas (colunas relevantes) — docs/cnpj-metadados.pdf
EMP_CNPJ_BASICO = 0
EMP_RAZAO_SOCIAL = 1

# IBGE → código interno RFB (tabela Municipios.zip da mesma ref; ex. Fortaleza-CE)
IBGE_TO_RFB_MUNICIPIO: dict[str, str] = {
    "2304400": "1389",  # Fortaleza
    "2304285": "1247",  # Eusébio
    "2303709": "1373",  # Caucaia
    "2301109": "1319",  # Aquiraz
    "2307650": "1585",  # Maracanaú
    "3303302": "5865",  # Niterói
    "3519070": "2951",  # Hortolândia-SP (código RFB confirmado no cno.csv)
    "3519071": "2951",  # Hortolândia-SP (IBGE com dígito verificador, via buscar_municipio)
}

DATA_DIR = _ROOT / "metrics" / "rfb_cnpj_cache"
UPSERT_BATCH = 1000
FLUSH_BUFFER = 2000


def _supabase_client():
    from supabase import create_client

    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        tried = ", ".join(str(p) for p in _ENV_CANDIDATES)
        loaded = ", ".join(str(p) for p in _BOOTSTRAPPED) or "(nenhum)"
        raise RuntimeError(
            "SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY são obrigatórios para gravar no Supabase. "
            f"Arquivos tentados: {tried}. Carregados: {loaded}. "
            f"Preencha {_ROOT / '.env'} (copie de .env.example; service_role NÃO é a anon key). "
            "Diagnóstico: python tools/_check_supabase_env.py"
        )
    return create_client(url, key)


def _normalize_ref_month(ref: str) -> str:
    if ref == "latest":
        # heurística simples: usa mês corrente (RFB pode estar 1 mês atrás)
        today = date.today()
        return f"{today.year:04d}-{today.month:02d}"
    # CLI costuma passar como int/float acidentalmente; normalize para str
    ref = str(ref).strip()
    if not re.match(r"^\d{4}-\d{2}$", ref):
        raise ValueError("--ref deve ser YYYY-MM ou 'latest'")
    return ref


def _is_valid_zip(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 4:
        return False
    try:
        with zipfile.ZipFile(path, "r") as zf:
            return bool(zf.namelist())
    except zipfile.BadZipFile:
        return False


def _expected_bytes(url: str, headers: dict) -> int:
    try:
        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            r = client.head(url, headers=headers)
            if r.status_code == 200:
                return int(r.headers.get("content-length") or 0)
    except Exception:
        pass
    return 0


def _download(url: str, dest: Path, *, headers: dict | None = None) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    h = {"User-Agent": "gymsite-intelligence/1.0 (cnpj fitness loader)"}
    if headers:
        h.update(headers)

    expected = _expected_bytes(url, h)
    if dest.exists() and dest.stat().st_size > 0:
        local = dest.stat().st_size
        if dest.suffix.lower() == ".zip" and _is_valid_zip(dest):
            return
        if expected and local >= expected:
            if dest.suffix.lower() == ".zip" and not _is_valid_zip(dest):
                print(f"[warn] ZIP corrompido, rebaixando: {dest}", flush=True)
                dest.unlink(missing_ok=True)
            else:
                return
        elif expected and local < expected:
            print(
                f"[info] retomando download: {local / (1024**2):.0f}/"
                f"{expected / (1024**2):.0f} MB",
                flush=True,
            )
        else:
            print(f"[warn] ZIP inválido/incompleto, rebaixando: {dest}", flush=True)
            dest.unlink(missing_ok=True)

    backoffs = [2, 5, 10]
    last_err: Exception | None = None
    for attempt, delay in enumerate(backoffs, start=1):
        try:
            _stream_download(url, dest, h, expected=expected)
            print(f"ok: {dest} ({dest.stat().st_size / (1024*1024):.1f} MB)", flush=True)
            if dest.suffix.lower() == ".zip" and not _is_valid_zip(dest):
                dest.unlink(missing_ok=True)
                raise RuntimeError(f"ZIP inválido após download: {dest}")
            return
        except Exception as e:
            last_err = e
            if attempt < len(backoffs):
                time.sleep(delay)
    raise RuntimeError(f"Falha ao baixar {url}: {last_err}")


def _stream_download(
    url: str, dest: Path, headers: dict, *, expected: int = 0
) -> None:
    resume_at = dest.stat().st_size if dest.exists() else 0
    req_headers = dict(headers)
    if resume_at > 0:
        req_headers["Range"] = f"bytes={resume_at}-"
    print(
        f"baixando: {url}"
        + (f" (resume {resume_at // (1024 * 1024)} MB)" if resume_at else ""),
        flush=True,
    )
    with httpx.stream(
        "GET", url, headers=req_headers, timeout=300.0, follow_redirects=True
    ) as r:
        if resume_at > 0 and r.status_code not in (200, 206):
            dest.unlink(missing_ok=True)
            return _stream_download(url, dest, headers, expected=expected)
        r.raise_for_status()
        total = expected or int(r.headers.get("content-length") or 0)
        if r.status_code == 206:
            cr = r.headers.get("content-range", "")
            m = re.search(r"/(\d+)\s*$", cr)
            if m:
                total = int(m.group(1))
        written = resume_at if r.status_code == 206 else 0
        if r.status_code == 200 and resume_at > 0:
            written = 0
        mode = "ab" if written > 0 else "wb"
        with dest.open(mode) as f:
            for chunk in r.iter_bytes():
                if chunk:
                    f.write(chunk)
                    written += len(chunk)
                    if total and written % (50 * 1024 * 1024) < len(chunk):
                        pct = 100.0 * written / total
                        print(
                            f"  … {written / (1024*1024):.0f}/"
                            f"{total / (1024*1024):.0f} MB ({pct:.0f}%)",
                            flush=True,
                        )


def _webdav_headers(token: str) -> dict:
    """Auth básica para share público Nextcloud WebDAV (user=token, senha vazia)."""
    auth = base64.b64encode((token + ":").encode("utf-8")).decode("ascii")
    return {"Authorization": "Basic " + auth}


def _iter_estabelecimentos_zip(zip_path: Path) -> Iterable[list[str]]:
    """
    Itera linhas do CSV dentro do ZIP.
    Layout é ';' e usualmente latin-1.
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        # pega o primeiro arquivo dentro do zip (normalmente .csv)
        names = [n for n in zf.namelist() if not n.endswith("/")]
        if not names:
            return
        with zf.open(names[0], "r") as f:
            text = io.TextIOWrapper(f, encoding="latin-1", errors="replace", newline="")
            reader = csv.reader(text, delimiter=";")
            for row in reader:
                yield row


def _build_cnpj(basico: str, ordem: str, dv: str) -> str:
    return f"{basico}{ordem}{dv}"


def _parse_date(s: str) -> str | None:
    # RFB usa YYYYMMDD; vazio ou lixo (ex. "0") vira None no Postgres
    s = (s or "").strip()
    if not s or s == "0":
        return None
    if re.match(r"^\d{8}$", s):
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    return None


def _resolve_municipio_codigo(codigo: str) -> str:
    """
    Estabelecimentos usam o código do município na tabela Municipios.zip (4 dígitos),
    não o código IBGE de 7 dígitos. Aceita ambos quando há mapeamento conhecido.
    """
    codigo = (codigo or "").strip()
    if not codigo:
        return ""
    if len(codigo) == 7 and codigo.isdigit():
        mapped = IBGE_TO_RFB_MUNICIPIO.get(codigo)
        if mapped:
            print(f"[info] municipio IBGE {codigo} -> codigo RFB {mapped}")
            return mapped
        raise ValueError(
            f"Código IBGE {codigo} sem mapeamento RFB. "
            f"Use --municipio-codigo com o código da tabela Municipios.zip "
            f"(Fortaleza-CE = 1389) ou acrescente em IBGE_TO_RFB_MUNICIPIO."
        )
    return codigo


def _match_cnae(principal: str, secundarios: str) -> bool:
    principal = (principal or "").strip()
    secundarios = (secundarios or "").strip()
    if principal == CNAE_ALVO:
        return True
    # secundários vêm separados por vírgula no layout
    return CNAE_ALVO in {c.strip() for c in secundarios.split(",") if c.strip()}


def _cache_dir(ref_month: str, local_dir: str) -> Path:
    return Path(local_dir) if local_dir else DATA_DIR / ref_month


def _zip_path(
    ref_month: str,
    part: int,
    *,
    local_dir: str,
) -> Path:
    return _cache_dir(ref_month, local_dir) / f"Estabelecimentos{part}.zip"


def _municipios_zip_path(ref_month: str, *, local_dir: str) -> Path:
    return _cache_dir(ref_month, local_dir) / "Municipios.zip"


def _empresas_zip_path(ref_month: str, part: int, *, local_dir: str) -> Path:
    return _cache_dir(ref_month, local_dir) / f"Empresas{part}.zip"


def _ensure_municipios_zip(
    ref_month: str,
    *,
    local_dir: str,
    rfb_share_token: str,
    rfb_webdav_base: str,
) -> Path:
    dest = _municipios_zip_path(ref_month, local_dir=local_dir)
    if dest.is_file() and dest.stat().st_size > 0:
        return dest
    webdav_base = (rfb_webdav_base or DEFAULT_WEBDAV_BASE).rstrip("/")
    headers = _webdav_headers(rfb_share_token) if rfb_share_token else None
    if rfb_share_token:
        url = f"{webdav_base}/{ref_month}/Municipios.zip"
    else:
        url = f"{BASE_URL}/{ref_month}/Municipios.zip"
    _download(url, dest, headers=headers)
    return dest


def _title_municipio(nome: str) -> str:
    """Normaliza nome RFB (geralmente MAIÚSCULO) para consultas por cidade."""
    nome = (nome or "").strip()
    if not nome:
        return ""
    lower = nome.lower()
    return " ".join(w[:1].upper() + w[1:] if w else "" for w in lower.split())


def _ensure_empresas_zip(
    ref_month: str,
    part: int,
    *,
    local_dir: str,
    rfb_share_token: str,
    rfb_webdav_base: str,
    skip_missing: bool,
) -> Path | None:
    dest = _empresas_zip_path(ref_month, part, local_dir=local_dir)
    if dest.is_file() and dest.stat().st_size > 0 and _is_valid_zip(dest):
        return dest
    webdav_base = (rfb_webdav_base or DEFAULT_WEBDAV_BASE).rstrip("/")
    headers = _webdav_headers(rfb_share_token) if rfb_share_token else None
    try:
        if rfb_share_token:
            url = f"{webdav_base}/{ref_month}/Empresas{part}.zip"
            _download(url, dest, headers=headers)
        else:
            url = f"{BASE_URL}/{ref_month}/Empresas{part}.zip"
            _download(url, dest)
        return dest
    except Exception as exc:
        if skip_missing:
            print(f"[skip] Empresas{part}.zip ausente ou falha: {exc}")
            return None
        raise


def _load_empresas_map(
    ref_month: str,
    parts: list[int],
    *,
    local_dir: str,
    rfb_share_token: str,
    rfb_webdav_base: str,
    skip_missing: bool,
) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for part in parts:
        path = _ensure_empresas_zip(
            ref_month,
            part,
            local_dir=local_dir,
            rfb_share_token=rfb_share_token,
            rfb_webdav_base=rfb_webdav_base,
            skip_missing=skip_missing,
        )
        if not path:
            continue
        print(f"[info] lendo razão social: {path.name}")
        count = 0
        for row in _iter_estabelecimentos_zip(path):
            if len(row) < 2:
                continue
            cnpj_basico = row[EMP_CNPJ_BASICO].strip()
            razao = row[EMP_RAZAO_SOCIAL].strip()
            if cnpj_basico and razao:
                mapping[cnpj_basico] = razao
                count += 1
        print(f"[info] Empresas{part}: {count} razões sociais carregadas")
    print(f"[info] total razões sociais em memória: {len(mapping)}")
    return mapping


def _load_municipios_map(
    ref_month: str,
    *,
    local_dir: str,
    rfb_share_token: str,
    rfb_webdav_base: str,
    nacional: bool,
) -> dict[str, str]:
    if not nacional:
        return {}
    path = _ensure_municipios_zip(
        ref_month,
        local_dir=local_dir,
        rfb_share_token=rfb_share_token,
        rfb_webdav_base=rfb_webdav_base,
    )
    mapping: dict[str, str] = {}
    for row in _iter_estabelecimentos_zip(path):
        if len(row) < 2:
            continue
        codigo = row[0].strip()
        nome = _title_municipio(row[1])
        if codigo and nome:
            mapping[codigo] = nome
    print(f"[info] Municipios.zip: {len(mapping)} municípios")
    return mapping


def _resolve_cidade(
    municipio_codigo: str,
    *,
    cidade_cli: str,
    municipios_map: dict[str, str],
) -> str:
    if cidade_cli:
        return cidade_cli
    return municipios_map.get((municipio_codigo or "").strip(), "")


def _upsert_rows(sb: Any, rows: list[dict], *, strip_segmento: bool) -> bool:
    """Grava lote no Supabase. Retorna strip_segmento atualizado."""
    if not rows:
        return strip_segmento
    for start in range(0, len(rows), UPSERT_BATCH):
        batch = rows[start : start + UPSERT_BATCH]
        if strip_segmento:
            batch = [{k: v for k, v in r.items() if k != "segmento_operacao"} for r in batch]
        try:
            sb.table("cnpj_fitness_estabelecimentos").upsert(
                batch,
                on_conflict="ref_month,cnpj",
            ).execute()
        except Exception as exc:
            msg = str(exc).lower()
            if not strip_segmento and "segmento_operacao" in msg:
                strip_segmento = True
                print(
                    "[warn] coluna segmento_operacao ausente — "
                    "db/migrations/20260528_cnpj_segmento_operacao.sql"
                )
                batch = [
                    {k: v for k, v in r.items() if k != "segmento_operacao"}
                    for r in batch
                ]
                sb.table("cnpj_fitness_estabelecimentos").upsert(
                    batch,
                    on_conflict="ref_month,cnpj",
                ).execute()
            else:
                raise
    return strip_segmento


def load_ref_month(
    ref_month: str,
    *,
    cidade: str,
    uf: str,
    municipio_codigo: str,
    local_dir: str,
    rfb_share_token: str,
    rfb_webdav_base: str,
    parts: list[int],
    dry_run: bool,
    skip_missing: bool,
    nacional: bool = False,
) -> int:
    """
    Baixa Estabelecimentos*.zip e upserta apenas linhas ativas com CNAE alvo.
    Retorna quantidade selecionada (gravada ou em dry-run).
    """
    ref_month = _normalize_ref_month(ref_month)
    ref_date = f"{ref_month}-01"
    municipio_filtro = _resolve_municipio_codigo(municipio_codigo) if municipio_codigo else ""
    uf_filter = "" if nacional else (uf or "").strip().upper()[:2]
    cidade_cli = "" if nacional else (cidade or "").strip()

    municipios_map = _load_municipios_map(
        ref_month,
        local_dir=local_dir,
        rfb_share_token=rfb_share_token,
        rfb_webdav_base=rfb_webdav_base,
        nacional=nacional,
    )

    empresas_map = _load_empresas_map(
        ref_month,
        parts or list(range(10)),
        local_dir=local_dir,
        rfb_share_token=rfb_share_token,
        rfb_webdav_base=rfb_webdav_base,
        skip_missing=skip_missing,
    )

    buffer: list[dict] = []
    total_selected = 0
    sb = None if dry_run else _supabase_client()
    strip_segmento = False
    total_upserted = 0

    def _flush() -> None:
        nonlocal strip_segmento, total_upserted
        if not buffer:
            return
        if dry_run:
            buffer.clear()
            return
        strip_segmento = _upsert_rows(sb, buffer, strip_segmento=strip_segmento)
        total_upserted += len(buffer)
        print(f"upsert acumulado: {total_upserted}")
        buffer.clear()

    webdav_base = (rfb_webdav_base or DEFAULT_WEBDAV_BASE).rstrip("/")
    webdav_headers = _webdav_headers(rfb_share_token) if rfb_share_token else None

    parts = parts or list(range(10))
    skipped: list[int] = []

    def _ensure_part_zip(part: int, path: Path) -> bool:
        """Baixa ou completa o ZIP. Retorna False se parte ignorada (--skip-missing)."""
        needs = (
            not path.is_file()
            or path.stat().st_size == 0
            or not _is_valid_zip(path)
        )
        if not needs:
            return True
        if path.is_file() and path.stat().st_size > 0:
            print(
                f"[info] {path.name} incompleto ou inválido — baixando/retomando",
                flush=True,
            )
        if rfb_share_token or not local_dir:
            if rfb_share_token:
                url = f"{webdav_base}/{ref_month}/Estabelecimentos{part}.zip"
                _download(url, path, headers=webdav_headers)
            else:
                url = f"{BASE_URL}/{ref_month}/Estabelecimentos{part}.zip"
                _download(url, path)
            return True
        if skip_missing:
            print(f"[skip] ausente: {path}")
            return False
        raise FileNotFoundError(
            f"ZIP não encontrado ou inválido: {path}. "
            "Use --rfb-share-token ou --skip-missing."
        )

    for i in parts:
        local = _zip_path(ref_month, i, local_dir=local_dir)
        if not _ensure_part_zip(i, local):
            skipped.append(i)
            continue

        print(f"processando: {local.name} ({local.stat().st_size / (1024**3):.2f} GB)")
        part_count = 0
        for row in _iter_estabelecimentos_zip(local):
            if len(row) <= EST_MUNICIPIO:
                continue

            basico = row[EST_CNPJ_BASICO]
            ordem = row[EST_CNPJ_ORDEM]
            dv = row[EST_CNPJ_DV]
            nome_fantasia = row[EST_NOME_FANTASIA] if len(row) > EST_NOME_FANTASIA else ""
            situacao = (row[EST_SITUACAO] if len(row) > EST_SITUACAO else "").strip()
            data_situacao = _parse_date(row[EST_DATA_SITUACAO] if len(row) > EST_DATA_SITUACAO else "")
            municipio = (row[EST_MUNICIPIO] if len(row) > EST_MUNICIPIO else "").strip()
            uf_row = (row[EST_UF] if len(row) > EST_UF else "").strip().upper()
            cep = (row[EST_CEP] if len(row) > EST_CEP else "").strip()
            tipo_log = row[EST_TIPO_LOGRADOURO] if len(row) > EST_TIPO_LOGRADOURO else ""
            logradouro = row[EST_LOGRADOURO] if len(row) > EST_LOGRADOURO else ""
            if tipo_log and logradouro:
                logradouro = f"{tipo_log} {logradouro}".strip()
            numero = row[EST_NUMERO] if len(row) > EST_NUMERO else ""
            complemento = row[EST_COMPLEMENTO] if len(row) > EST_COMPLEMENTO else ""
            bairro = (row[EST_BAIRRO] if len(row) > EST_BAIRRO else "").strip()
            ddd1 = (row[EST_DDD1] if len(row) > EST_DDD1 else "").strip()
            tel1 = (row[EST_TELEFONE1] if len(row) > EST_TELEFONE1 else "").strip()
            email = (row[EST_EMAIL] if len(row) > EST_EMAIL else "").strip()
            telefone = None
            if tel1:
                telefone = f"{ddd1}{tel1}" if ddd1 else tel1
            data_inicio = _parse_date(row[EST_DATA_INICIO] if len(row) > EST_DATA_INICIO else "")
            cnae_principal = (row[EST_CNAE_PRINCIPAL] if len(row) > EST_CNAE_PRINCIPAL else "").strip()
            cnae_sec = (row[EST_CNAE_SECUNDARIA] if len(row) > EST_CNAE_SECUNDARIA else "").strip()

            if municipio_filtro and municipio != municipio_filtro:
                continue
            if uf_filter and uf_row != uf_filter:
                continue
            if situacao not in SITUACAO_ATIVA:
                continue
            if not _match_cnae(cnae_principal, cnae_sec):
                continue

            segmento = classificar_segmento(
                nome_fantasia, cnae_principal, cnae_sec
            ).segmento

            cidade_row = _resolve_cidade(
                municipio, cidade_cli=cidade_cli, municipios_map=municipios_map
            )

            cnpj_completo = _build_cnpj(basico, ordem, dv)
            razao_social = empresas_map.get(basico, "").strip() or None
            buffer.append(
                {
                    "ref_month": ref_date,
                    "cnpj": cnpj_completo,
                    "municipio_codigo": municipio,
                    "uf": uf_row,
                    "cidade": cidade_row,
                    "cnae_fiscal_principal": cnae_principal,
                    "cnaes_secundarios": cnae_sec,
                    "data_inicio_atividade": data_inicio,
                    "situacao_cadastral": int(situacao) if situacao.isdigit() else None,
                    "data_situacao_cadastral": data_situacao,
                    "nome_fantasia": nome_fantasia,
                    "razao_social": razao_social,
                    "cep": cep,
                    "logradouro": logradouro,
                    "numero": numero,
                    "complemento": complemento,
                    "bairro": bairro or None,
                    "email": email or None,
                    "telefone": telefone,
                    "segmento_operacao": segmento,
                }
            )
            total_selected += 1
            part_count += 1
            if len(buffer) >= FLUSH_BUFFER:
                _flush()

        print(f"  parte {i}: {part_count} fitness selecionados")
        _flush()

    if skipped:
        print(f"[info] partes ignoradas (ZIP ausente): {skipped}")

    if dry_run:
        print(f"[dry-run] selecionados: {total_selected}")
        return total_selected

    return total_upserted or total_selected


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Loader CNPJ fitness (RFB) → Supabase")
    ap.add_argument("--ref", default="latest", help="YYYY-MM ou 'latest'")
    ap.add_argument("--cidade", help="Nome da cidade (ex: Fortaleza)")
    ap.add_argument("--uf", help="UF (ex: CE)")
    ap.add_argument(
        "--municipio-codigo",
        default="",
        help="Código do município na tabela Municipios.zip (RFB). Fortaleza-CE=1389; "
        "IBGE 2304400 também é aceito (mapeado automaticamente).",
    )
    ap.add_argument(
        "--local-dir",
        default="",
        help="Diretório com Estabelecimentos0..9.zip já baixados (evita download).",
    )
    ap.add_argument(
        "--rfb-share-token",
        default="",
        help="Token de share WebDAV da Receita (Nextcloud). Ex: YggdBLfdninEJX9",
    )
    ap.add_argument(
        "--rfb-webdav-base",
        default=DEFAULT_WEBDAV_BASE,
        help="Base WebDAV (default: arquivos.receitafederal.gov.br/public.php/webdav)",
    )
    ap.add_argument(
        "--parts",
        default="0,1,2,3,4,5,6,7,8,9",
        help="Quais partes Estabelecimentos baixar/ler (ex: 0 ou 0,1,2). Default: 0-9.",
    )
    ap.add_argument("--dry-run", action="store_true", help="Não grava no Supabase")
    ap.add_argument(
        "--nacional",
        action="store_true",
        help="Carga Brasil inteiro: dispensa --cidade/--uf, resolve cidade via Municipios.zip",
    )
    ap.add_argument(
        "--skip-missing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Com --local-dir, ignora partes cujo ZIP não existe (default: true).",
    )
    ap.add_argument(
        "--check-env",
        action="store_true",
        help="Só verifica se SUPABASE_* está no .env e sai (0=ok).",
    )
    args = ap.parse_args(argv)

    if args.check_env:
        url = (os.getenv("SUPABASE_URL") or "").strip()
        key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
        print("env files loaded:", _BOOTSTRAPPED or "(nenhum)")
        print("SUPABASE_URL:", "ok" if url else "MISSING")
        print("SUPABASE_SERVICE_ROLE_KEY:", "ok" if key else "MISSING")
        return 0 if url and key else 1

    if not args.nacional and (not args.cidade or not args.uf):
        ap.error("--cidade e --uf são obrigatórios (use --nacional para carga Brasil)")

    parts: list[int] = []
    for p in str(args.parts).split(","):
        p = p.strip()
        if not p:
            continue
        if not p.isdigit() or int(p) < 0 or int(p) > 9:
            raise SystemExit("--parts deve conter inteiros 0..9 separados por vírgula")
        parts.append(int(p))

    n = load_ref_month(
        args.ref,
        cidade=args.cidade or "",
        uf=args.uf or "",
        municipio_codigo=args.municipio_codigo,
        local_dir=args.local_dir,
        rfb_share_token=args.rfb_share_token,
        rfb_webdav_base=args.rfb_webdav_base,
        parts=parts,
        dry_run=args.dry_run,
        skip_missing=args.skip_missing,
        nacional=args.nacional,
    )
    print("done:", n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

