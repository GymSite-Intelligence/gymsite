"""
Loader de CNO FRESCO via RFB bulk (dadosabertos.rfb.gov.br/CNO) → Supabase.

O basedosdados.br_me_cno é defasado (≤2021); para demanda futura (Apêndice B) precisa
da fonte VIVA da Receita (atualização mensal). Portal bulk RFB é aberto, SEM token —
mesma casa de onde o CNPJ já baixa (rfb_cnpj_fitness_loader). Geo-block fora do Brasil:
roda no cron CI / máquina BR, não no sandbox.

Baixa zip → extrai cno.csv → classifica NACIONAL (fitness + grande-porte residencial) →
upsert public.cno_obras_fitness + public.cno_obras_grande_porte. Reusa o parser do
extract local (cno_fitness_tools._map_headers/_val) e a classificação (_eh_obra_fitness).

Uso:
    python -m tools.rfb_cno_loader                      # auto-descobre zip mais recente
    CNO_BULK_ZIP_URL=https://.../cno.zip python -m tools.rfb_cno_loader
    python -m tools.rfb_cno_loader --cno-dir D:/dados/cno_extract   # extract já baixado
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import zipfile
from pathlib import Path
from typing import Any, Iterator

import httpx

from tools.cno_fitness_tools import (
    _KEYWORDS_OBRA_FITNESS,
    _digits,
    _eh_obra_fitness,
    _float,
    _map_headers,
    _situacao_label,
    _val,
)
from tools.cno_bigquery_loader import _KW_COMERCIAL, _AREA_GP_MAX, _AREA_GP_MIN, _SITUACAO_EM_CURSO
from tools.rfb_cnpj_fitness_loader import IBGE_TO_RFB_MUNICIPIO, _is_valid_zip, _stream_download
from tools.db_schema import tbl

CNO_INDEX_URL = os.environ.get("CNO_BULK_INDEX_URL", "https://dadosabertos.rfb.gov.br/CNO/")
_FITNESS_KW = tuple(k for k in _KEYWORDS_OBRA_FITNESS)


def _carregar_crosswalk_rf_ibge() -> dict[str, str]:
    """Crosswalk RFB→IBGE completo (5570) de data/municipio_rf_ibge.json;
    fallback ao mapa estático parcial. Gerado de basedosdados (timeless)."""
    p = Path(__file__).resolve().parent.parent / "data" / "municipio_rf_ibge.json"
    base = {v: k for k, v in IBGE_TO_RFB_MUNICIPIO.items()}  # fallback parcial
    try:
        import json as _json

        full = _json.loads(p.read_text(encoding="utf-8"))
        if isinstance(full, dict):
            base.update({str(k): str(v) for k, v in full.items()})
    except (OSError, ValueError):
        pass
    return base


_RFB_TO_IBGE = _carregar_crosswalk_rf_ibge()


def descobrir_zip_url() -> str:
    """URL do zip CNO mais recente. Override por CNO_BULK_ZIP_URL; senão varre o índice."""
    override = (os.environ.get("CNO_BULK_ZIP_URL") or "").strip()
    if override:
        return override
    with httpx.Client(timeout=60.0, follow_redirects=True) as c:
        html = c.get(CNO_INDEX_URL).text
    zips = re.findall(r'href="([^"]+\.zip)"', html, flags=re.I)
    if not zips:
        raise RuntimeError(f"nenhum .zip em {CNO_INDEX_URL} — defina CNO_BULK_ZIP_URL")
    # mais recente: ordena por nome (datas YYYY-MM ou versão no nome) — pega o último.
    alvo = sorted(zips)[-1]
    return alvo if alvo.startswith("http") else CNO_INDEX_URL.rstrip("/") + "/" + alvo.lstrip("/")


_MANUAL_MSG = (
    "Download automático do CNO falhou (host RFB sem resposta/geo-block).\n"
    "  → Baixe o cno.zip manual no navegador:\n"
    "      https://www.gov.br/receitafederal/pt-br/assuntos/orientacao-tributaria/cadastros/cno\n"
    "    (ou dados.gov.br > Cadastro Nacional de Obras CNO > recurso .zip)\n"
    "  → Extraia em uma pasta (ex.: D:\\dados\\cno_extract) e rode:\n"
    "      python -m tools.rfb_cno_loader --cno-dir D:\\dados\\cno_extract\n"
    "  → Ou, se souber a URL direta do .zip:\n"
    "      $env:CNO_BULK_ZIP_URL='https://.../cno.zip'; python -m tools.rfb_cno_loader"
)


def baixar_e_extrair(workdir: Path) -> Path:
    """Baixa o zip CNO e extrai; retorna a pasta com cno.csv."""
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        url = descobrir_zip_url()
        zpath = workdir / "cno.zip"
        _stream_download(url, zpath, {"User-Agent": "gymsite-intelligence/1.0"})
    except (httpx.HTTPError, RuntimeError, OSError) as e:
        raise SystemExit(f"[rfb_cno_loader] {type(e).__name__}: {e}\n\n{_MANUAL_MSG}") from e
    if not _is_valid_zip(zpath):
        raise RuntimeError(f"zip inválido: {zpath}")
    with zipfile.ZipFile(zpath) as z:
        z.extractall(workdir)
    return workdir


def _ibge_do_rfb(rfb_code: str) -> str | None:
    return _RFB_TO_IBGE.get((rfb_code or "").strip())


def _sniff_delim(header_line: str) -> str:
    """RFB usa ';'; extract convertido pode ser ','. Detecta pelo header."""
    return ";" if header_line.count(";") >= header_line.count(",") else ","


def _linhas_cno(cno_dir: Path) -> Iterator[dict[str, str]]:
    main = cno_dir / "cno.csv"
    if not main.is_file():
        raise FileNotFoundError(f"cno.csv ausente em {cno_dir}")
    with open(main, encoding="latin-1", errors="replace") as f:
        first = f.readline()
        delim = _sniff_delim(first)
        f.seek(0)
        reader = csv.DictReader(f, delimiter=delim)
        hdr = _map_headers(reader.fieldnames or [])
        for row in reader:
            yield {k: _val(row, hdr, k) for k in
                   ("cno", "cep", "nome", "area", "municipio", "cnpj",
                    "logradouro", "numero", "bairro", "data_inicio", "situacao", "data_situacao")}


def _is_comercial(nome: str) -> bool:
    n = (nome or "").lower()
    return any(k in n for k in _KW_COMERCIAL)


def _is_fitness_kw(nome: str) -> bool:
    n = (nome or "").lower()
    return any(k in n for k in _FITNESS_KW)


def _base_row(r: dict, *, extra: dict | None = None) -> dict:
    rfb = (r.get("municipio") or "").strip()
    sit = (r.get("situacao") or "").strip().zfill(2) if r.get("situacao") else ""
    base = {
        "id_cno": r.get("cno"),
        "nome": (r.get("nome") or "").strip() or None,
        "area_m2": _float(r.get("area")) or None,
        "cep": _digits(r.get("cep") or "") or None,
        "logradouro": r.get("logradouro") or None,
        "numero_logradouro": r.get("numero") or None,
        "bairro": r.get("bairro") or None,
        "id_municipio": _ibge_do_rfb(rfb),
        "id_municipio_rf": rfb or None,
        "situacao": sit or None,
        "em_curso": sit in _SITUACAO_EM_CURSO,
        "data_inicio": (r.get("data_inicio") or None),
        "data_situacao": (r.get("data_situacao") or None),
        "ni_responsavel": _digits(r.get("cnpj") or "") or None,
        "fonte": "dadosabertos.rfb.gov.br/CNO",
    }
    if extra:
        base.update(extra)
    return base


def classificar(cno_dir: Path) -> dict[str, list[dict]]:
    """Varre cno.csv nacional → {fitness:[...], grande_porte:[...]}."""
    fitness: list[dict] = []
    gp: list[dict] = []
    for r in _linhas_cno(cno_dir):
        if not r.get("cno"):
            continue
        nome = r.get("nome") or ""
        area = _float(r.get("area"))
        eh, metodo = _eh_obra_fitness(nome, area, None)
        if eh:
            fitness.append(_base_row(r, extra={"nome_empresarial": nome or None,
                                               "metodo_classificacao": metodo}))
            continue
        # grande porte residencial: faixa de área + em curso + não-comercial.
        sit = (r.get("situacao") or "").strip().zfill(2)
        if (_AREA_GP_MIN <= area <= _AREA_GP_MAX and sit in _SITUACAO_EM_CURSO
                and not _is_comercial(nome) and not _is_fitness_kw(nome)):
            gp.append(_base_row(r))
    return {"fitness": fitness, "grande_porte": gp}


def _supabase():
    from tools.supabase_client import load_create_client

    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
           or os.environ.get("SUPABASE_KEY"))
    return load_create_client()(os.environ["SUPABASE_URL"], key)


def _upsert(cli, tabela: str, rows: list[dict], chunk: int = 500) -> int:
    n = 0
    for i in range(0, len(rows), chunk):
        tbl(cli, tabela).upsert(rows[i:i + chunk], on_conflict="id_cno").execute()
        n += len(rows[i:i + chunk])
    return n


def minerar(*, cno_dir: str | Path | None = None, dry_run: bool = False) -> dict:
    workdir = Path(cno_dir) if cno_dir else Path(os.environ.get("CNO_DATA_DIR") or "./.cno_fresh")
    if not (workdir / "cno.csv").is_file():
        baixar_e_extrair(workdir)
    classes = classificar(workdir)
    out = {"fitness": len(classes["fitness"]), "grande_porte": len(classes["grande_porte"]),
           "fitness_upserted": 0, "grande_porte_upserted": 0}
    if dry_run:
        return out
    cli = _supabase()
    out["fitness_upserted"] = _upsert(cli, "cno_obras_fitness", classes["fitness"])
    out["grande_porte_upserted"] = _upsert(cli, "cno_obras_grande_porte", classes["grande_porte"])
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Minera CNO FRESCO (RFB bulk) → Supabase")
    p.add_argument("--cno-dir", default=None, help="pasta com cno.csv já extraído")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    r = minerar(cno_dir=args.cno_dir, dry_run=args.dry_run)
    print(f"fitness={r['fitness']} (upsert {r['fitness_upserted']}) | "
          f"grande_porte={r['grande_porte']} (upsert {r['grande_porte_upserted']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
