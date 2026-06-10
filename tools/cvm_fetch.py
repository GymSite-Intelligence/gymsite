"""
Fetch estruturado CVM (cadastro + ITR DRE/BPA/BPP) para empresas listadas.

Fase B2: SMFT3 (Smart Fit) via dados.cvm.gov.br — sem scrape de RI.
"""
from __future__ import annotations

import csv
import io
import logging
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable

import httpx

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
CVM_CACHE_DIR = ROOT / "metrics" / "cache" / "cvm"

CAD_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv"
ITR_INDEX_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/DADOS/"

# Bluefit/Bio Ritmo/Bodytech não são SMFT3; BFFT3 IPO interrompido — só Smart Fit listada.
TICKER_ALIASES: dict[str, str] = {
    "SMFT3": "SMARTFIT",
}

# Contas DFP (consolidado) — YTD no último trimestre do ano fiscal.
DRE_RECEITA = "3.01"
DRE_EBIT = "3.05"
DRE_DEPRECIACAO_DFC = "6.01.01.02"
BPP_EMPRESTIMOS_CP = "2.01.04"
BPP_EMPRESTIMOS_LP = "2.02.01"
BPA_CAIXA = "1.01.01"


@dataclass(frozen=True)
class CompanyRef:
    ticker: str
    cd_cvm: str
    cnpj: str
    denom_social: str


def _normalize_cnpj(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def _normalize_cd_cvm(value: str | None) -> str:
    digits = re.sub(r"\D", "", value or "")
    return digits.lstrip("0") or digits


def _normalize_ordem(value: str | None) -> str:
    s = (value or "").upper()
    s = s.replace("Ú", "U").replace("Û", "U").replace("ú", "U")
    return s


def _parse_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def _read_csv_text(text: str) -> csv.DictReader:
    return csv.DictReader(io.StringIO(text), delimiter=";")


def fetch_cad_rows(*, client: httpx.Client | None = None) -> list[dict[str, str]]:
    own = client is None
    client = client or httpx.Client(timeout=60.0, follow_redirects=True)
    try:
        r = client.get(CAD_URL)
        r.raise_for_status()
        r.encoding = "latin-1"
        return list(_read_csv_text(r.text))
    finally:
        if own:
            client.close()


def resolve_company(
    ticker: str,
    *,
    cad_rows: Iterable[dict[str, str]] | None = None,
    client: httpx.Client | None = None,
) -> CompanyRef | None:
    """Resolve ticker B3 → CD_CVM + CNPJ via cad_cia_aberta."""
    ticker = (ticker or "").strip().upper()
    needle = TICKER_ALIASES.get(ticker)
    if not needle:
        return None

    rows = list(cad_rows) if cad_rows is not None else fetch_cad_rows(client=client)
    best: dict[str, str] | None = None
    for row in rows:
        denom = (row.get("DENOM_SOCIAL") or "").upper().replace(" ", "")
        if needle not in denom:
            continue
        if (row.get("SIT") or "").upper() != "ATIVO":
            continue
        if best is None or "BOLSA" in (row.get("TP_MERC") or "").upper():
            best = row

    if not best:
        return None

    return CompanyRef(
        ticker=ticker,
        cd_cvm=_normalize_cd_cvm(best.get("CD_CVM")),
        cnpj=_normalize_cnpj(best.get("CNPJ_CIA")),
        denom_social=(best.get("DENOM_SOCIAL") or "").strip(),
    )


def list_itr_zip_names(html: str) -> list[str]:
    return re.findall(r'href="(itr_cia_aberta_\d{4}\.zip)"', html, re.I)


def _itr_zip_url(name: str) -> str:
    return ITR_INDEX_URL + name


def _year_from_zip(name: str) -> int:
    m = re.search(r"(\d{4})", name)
    return int(m.group(1)) if m else 0


def download_itr_year(
    year: int,
    *,
    client: httpx.Client | None = None,
    cache_dir: Path | None = None,
) -> bytes | None:
    cache_dir = cache_dir or CVM_CACHE_DIR
    cache_path = cache_dir / f"itr_{year}.zip"
    if cache_path.is_file():
        return cache_path.read_bytes()

    own = client is None
    client = client or httpx.Client(timeout=120.0, follow_redirects=True)
    try:
        idx = client.get(ITR_INDEX_URL)
        idx.raise_for_status()
        names = list_itr_zip_names(idx.text)
        target = f"itr_cia_aberta_{year}.zip"
        if target not in names:
            return None
        r = client.get(_itr_zip_url(target))
        r.raise_for_status()
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(r.content)
        return r.content
    finally:
        if own:
            client.close()


def _row_matches_company(row: dict[str, str], ref: CompanyRef) -> bool:
    cnpj = _normalize_cnpj(row.get("CNPJ_CIA"))
    cd = _normalize_cd_cvm(row.get("CD_CVM"))
    return cnpj == ref.cnpj or (cd and cd == ref.cd_cvm)


def _is_ytd_ultimo(row: dict[str, str], dt_refer: str) -> bool:
    ordem = _normalize_ordem(row.get("ORDEM_EXERC"))
    if "ULTIMO" not in ordem:
        return False
    dt_fim = (row.get("DT_FIM_EXERC") or "").strip()
    if dt_fim != dt_refer:
        return False
    dt_ini = (row.get("DT_INI_EXERC") or "").strip()
    if not dt_ini or not dt_refer:
        return False
    # YTD: início no 1º dia do ano da DT_REFER
    return dt_ini.startswith(dt_refer[:4])


def _is_balance_ultimo(row: dict[str, str], dt_refer: str) -> bool:
    """BPA/BPP: posição na DT_REFER (DT_INI_EXERC frequentemente vazio)."""
    ordem = _normalize_ordem(row.get("ORDEM_EXERC"))
    if "ULTIMO" not in ordem:
        return False
    dt_fim = (row.get("DT_FIM_EXERC") or "").strip()
    return dt_fim == dt_refer


def _collect_account_rows(
    rows: Iterable[dict[str, str]],
    ref: CompanyRef,
    cd_conta: str,
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in rows:
        if not _row_matches_company(row, ref):
            continue
        if (row.get("CD_CONTA") or "").strip() != cd_conta:
            continue
        out.append(row)
    return out


def _latest_period(rows: list[dict[str, str]]) -> str | None:
    periods = sorted({(r.get("DT_REFER") or "").strip() for r in rows if r.get("DT_REFER")})
    return periods[-1] if periods else None


def _value_ytd(rows: list[dict[str, str]], cd_conta: str, dt_refer: str) -> float | None:
    for row in rows:
        if (row.get("CD_CONTA") or "").strip() != cd_conta:
            continue
        if (row.get("DT_REFER") or "").strip() != dt_refer:
            continue
        if not _is_ytd_ultimo(row, dt_refer):
            continue
        return _parse_float(row.get("VL_CONTA"))
    return None


def _value_balance(rows: list[dict[str, str]], cd_conta: str, dt_refer: str) -> float | None:
    for row in rows:
        if (row.get("CD_CONTA") or "").strip() != cd_conta:
            continue
        if (row.get("DT_REFER") or "").strip() != dt_refer:
            continue
        if not _is_balance_ultimo(row, dt_refer):
            continue
        return _parse_float(row.get("VL_CONTA"))
    return None


def _read_zip_csv(zip_bytes: bytes, pattern: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        name = next((n for n in zf.namelist() if pattern in n and n.lower().endswith(".csv")), None)
        if not name:
            return []
        text = zf.read(name).decode("latin-1", errors="replace")
        return list(_read_csv_text(text))


def extract_financials_from_itr(
    zip_bytes: bytes,
    ref: CompanyRef,
) -> dict[str, Any] | None:
    dre = _read_zip_csv(zip_bytes, "DRE_con")
    bpp = _read_zip_csv(zip_bytes, "BPP_con")
    bpa = _read_zip_csv(zip_bytes, "BPA_con")
    dfc = _read_zip_csv(zip_bytes, "DFC_MI_con")

    dre_co = [r for r in dre if _row_matches_company(r, ref)]
    if not dre_co:
        return None

    dt_refer = _latest_period(dre_co)
    if not dt_refer:
        return None

    receita = _value_ytd(dre_co, DRE_RECEITA, dt_refer)
    ebit = _value_ytd(dre_co, DRE_EBIT, dt_refer)
    deprec = _value_ytd(
        [r for r in dfc if _row_matches_company(r, ref)],
        DRE_DEPRECIACAO_DFC,
        dt_refer,
    )

    bpa_co = [r for r in bpa if _row_matches_company(r, ref)]
    bpp_co = [r for r in bpp if _row_matches_company(r, ref)]
    caixa = _value_balance(bpa_co, BPA_CAIXA, dt_refer)
    emp_cp = _value_balance(bpp_co, BPP_EMPRESTIMOS_CP, dt_refer)
    emp_lp = _value_balance(bpp_co, BPP_EMPRESTIMOS_LP, dt_refer)

    escala = next((r.get("ESCALA_MOEDA") for r in dre_co if r.get("ESCALA_MOEDA")), "MIL")

    ebitda = None
    margem_ebitda_pct = None
    if ebit is not None:
        dep = deprec or 0.0
        ebitda = ebit + dep
        if receita and receita > 0:
            margem_ebitda_pct = round(100.0 * ebitda / receita, 2)

    divida_bruta = None
    divida_liquida = None
    divida_liquida_ebitda = None
    if emp_cp is not None or emp_lp is not None:
        divida_bruta = (emp_cp or 0.0) + (emp_lp or 0.0)
        if caixa is not None:
            divida_liquida = divida_bruta - caixa
        if ebitda and ebitda > 0 and divida_liquida is not None:
            # Anualiza EBITDA YTD pelo número de meses no período
            months = int(dt_refer[5:7]) or 12
            ebitda_anual = ebitda * (12.0 / months)
            divida_liquida_ebitda = round(divida_liquida / ebitda_anual, 2)

    return {
        "periodo_ref": dt_refer,
        "escala_moeda": escala,
        "receita_liquida_mil": receita,
        "ebitda_mil": ebitda,
        "margem_ebitda_pct": margem_ebitda_pct,
        "divida_bruta_mil": divida_bruta,
        "caixa_mil": caixa,
        "divida_liquida_mil": divida_liquida,
        "divida_liquida_ebitda": divida_liquida_ebitda,
    }


def fetch_smft3_itr_metrics(
    *,
    client: httpx.Client | None = None,
    min_year: int = 2020,
) -> dict[str, Any] | None:
    """Baixa ITR mais recente com demonstrativos da Smart Fit."""
    own = client is None
    client = client or httpx.Client(timeout=120.0, follow_redirects=True)
    try:
        ref = resolve_company("SMFT3", client=client)
        if not ref:
            logger.warning("cvm_fetch: SMFT3 não encontrada no cadastro CVM")
            return None

        idx = client.get(ITR_INDEX_URL)
        idx.raise_for_status()
        years = sorted(
            (_year_from_zip(n), n) for n in list_itr_zip_names(idx.text)
        )
        best: dict[str, Any] | None = None
        best_score = -1
        for year, _ in reversed(years):
            if year < min_year:
                break
            blob = download_itr_year(year, client=client)
            if not blob:
                continue
            fin = extract_financials_from_itr(blob, ref)
            if not fin:
                continue
            score = 0
            if fin.get("margem_ebitda_pct") is not None:
                score += 2
            if fin.get("divida_liquida_ebitda") is not None:
                score += 1
            if score > best_score or (
                score == best_score
                and best
                and (fin.get("periodo_ref") or "") > (best.get("periodo_ref") or "")
            ):
                best_score = score
                best = {
                    "ticker": ref.ticker,
                    "cd_cvm": ref.cd_cvm,
                    "cnpj": ref.cnpj,
                    "denom_social": ref.denom_social,
                    "itr_ano": year,
                    **fin,
                }
        return best
    finally:
        if own:
            client.close()


def build_sector_listed_payload(metrics: dict[str, Any] | None) -> dict[str, Any]:
    """Monta JSON sector_listed compatível com cvm_listed_metrics."""
    base: dict[str, Any] = {
        "version": "1.1",
        "fonte": "CVM ITR (dados.cvm.gov.br)",
        "data_coleta": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "empresas": [],
        "links_oficiais": {
            "cvm_dados": "https://dados.cvm.gov.br/dataset/?q=ITR",
            "ri_smartfit": "https://ri.smartfit.com.br/",
        },
        "notas_setor": (
            "Peers Bluefit/Bio Ritmo/Bodytech não possuem ticker B3 comparável; "
            "KPIs operacionais (alunos, churn, ARPU) exigem RI — fora do escopo B2."
        ),
    }
    if not metrics:
        return base

    kpis: dict[str, Any] = {
        "margem_ebitda_pct": metrics.get("margem_ebitda_pct"),
        "divida_liquida_ebitda": metrics.get("divida_liquida_ebitda"),
        "capex_por_unidade_brl": None,
        "alunos_ativos": None,
        "churn_pct": None,
        "arpu_brl": None,
    }
    base["empresas"] = [
        {
            "nome": "Smart Fit",
            "ticker": "SMFT3",
            "cd_cvm": metrics.get("cd_cvm"),
            "periodo_ref": metrics.get("periodo_ref"),
            "itr_ano": metrics.get("itr_ano"),
            "fonte": "CVM ITR DRE/BPP/BPA",
            "kpis": kpis,
            "detalhes_cvm": {
                k: metrics.get(k)
                for k in (
                    "receita_liquida_mil",
                    "ebitda_mil",
                    "divida_liquida_mil",
                    "escala_moeda",
                )
                if metrics.get(k) is not None
            },
            "notas": (
                "margem_ebitda_pct = (EBIT YTD + depreciação DFC) / receita YTD; "
                "divida_liquida_ebitda anualizada pelo mês de DT_REFER."
            ),
        }
    ]
    return base


def atualizar_sector_listed_via_cvm(*, offline: bool = False) -> dict[str, Any]:
    """
    Fetch CVM e persiste sector_listed.json.
    offline=True: não chama rede (útil em testes).
    """
    from tools.cvm_listed_metrics import save_sector_listed_snapshot

    if offline:
        payload = build_sector_listed_payload(None)
        save_sector_listed_snapshot(payload)
        return payload

    metrics = fetch_smft3_itr_metrics()
    payload = build_sector_listed_payload(metrics)
    if not metrics:
        logger.warning("cvm_fetch: sem métricas ITR; snapshot vazio de empresas")
    save_sector_listed_snapshot(payload)
    return payload
