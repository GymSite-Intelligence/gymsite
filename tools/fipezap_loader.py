# tools/fipezap_loader.py
"""
Loader de dados do Índice FipeZap para Supabase.

Fluxo:
  1. Baixa (ou recebe path) do Excel fipezap-serieshistoricas.xlsx
  2. Faz parse de cada aba de cidade
  3. Extrai: venda_residencial, locacao_residencial, venda_comercial, locacao_comercial
  4. Faz upsert na tabela `fipezap_indices`

Uso manual:
  python tools/fipezap_loader.py --file docs/fipezap-serieshistoricas.xlsx --dry-run

Uso com download automático:
  python tools/fipezap_loader.py --download

Agendamento (crontab / Windows Task Scheduler):
  Mensal, dia 10 de cada mês (FipeZap publica entre dia 5-10)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
from dotenv import load_dotenv
from supabase import Client, create_client

# ── Configuração ────────────────────────────────────────────────────────────
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

FIPEZAP_URL = "https://downloads.fipe.org.br/indices/fipezap/fipezap-serieshistoricas.xlsx"

logger = logging.getLogger("fipezap_loader")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# Mapeamento de colunas do Excel (baseado na estrutura maio/2026)
# Cada entrada: (tipo_indice, coluna_base) onde coluna_base é a coluna "Total"
# do respectivo bloco. Variações e preço médio são derivados.
COL_MAPPING = {
    "venda_residencial": {
        "indice": 2,
        "var_mensal": 7,
        "var_12m": 12,
        "preco_medio": 17,
    },
    "locacao_residencial": {
        "indice": 22,
        "var_mensal": 27,
        "var_12m": 32,
        "preco_medio": 37,
    },
    "rentabilidade_residencial": {
        "indice": 42,  # rental yield residencial
        "var_mensal": None,
        "var_12m": None,
        "preco_medio": None,
    },
    "venda_comercial": {
        "indice": 47,
        "var_mensal": 48,
        "var_12m": 49,
        "preco_medio": 50,
    },
    "locacao_comercial": {
        "indice": 51,
        "var_mensal": 52,
        "var_12m": 53,
        "preco_medio": 54,
    },
    "rentabilidade_comercial": {
        "indice": 55,  # rental yield comercial
        "var_mensal": None,
        "var_12m": None,
        "preco_medio": None,
    },
}

# Abas a ignorar (não são cidades)
SKIP_SHEETS = {"Resumo", "Aux", "Índice FipeZAP"}


def download_excel(url: str = FIPEZAP_URL, dest_path: Path | None = None) -> Path:
    """Baixa o Excel do FipeZap para um arquivo temporário ou path especificado."""
    if dest_path is None:
        dest_path = Path(tempfile.gettempdir()) / "fipezap-serieshistoricas.xlsx"

    logger.info("Baixando %s → %s", url, dest_path)
    with httpx.stream("GET", url, follow_redirects=True, timeout=120) as response:
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=8192):
                f.write(chunk)

    logger.info("Download concluído: %.2f MB", dest_path.stat().st_size / 1_048_576)
    return dest_path


def parse_cidade_sheet(df: pd.DataFrame, sheet_name: str) -> list[dict[str, Any]]:
    """
    Faz parse de uma aba de cidade do Excel FipeZap.

    Estrutura esperada:
      - Linha 1 (índice 1 no pandas header=None): Data na coluna 1
      - A partir da linha 4: dados mensais
    """
    records: list[dict[str, Any]] = []

    # Normalizar nome da cidade (corrige encoding quebrado do Excel)
    cidade_nome = _normalizar_cidade(sheet_name.strip())

    # Detectar UF a partir do nome da cidade (heurística simples)
    uf = _inferir_uf(cidade_nome)

    # Dados começam na linha 4 (índice 4) quando usamos header=None
    for row_idx in range(4, len(df)):
        row = df.iloc[row_idx]
        data_val = row.iloc[1]

        if pd.isna(data_val):
            continue

        # Converter para data
        if isinstance(data_val, datetime):
            data_ref = data_val.date()
        elif isinstance(data_val, str):
            try:
                data_ref = datetime.strptime(data_val.strip(), "%Y-%m-%d").date()
            except ValueError:
                continue
        else:
            # Excel serial number
            try:
                data_ref = pd.to_datetime(data_val).date()
            except Exception:
                continue

        for tipo_indice, cols in COL_MAPPING.items():
            record: dict[str, Any] = {
                "cidade": cidade_nome,
                "uf": uf,
                "tipo_indice": tipo_indice,
                "data_referencia": data_ref.isoformat(),
            }

            # Índice (sempre presente)
            val_indice = row.iloc[cols["indice"]]
            if pd.notna(val_indice) and str(val_indice).strip() not in (".", "", "-"):
                try:
                    record["numero_indice"] = float(val_indice)
                except ValueError:
                    pass

            # Variação mensal
            if cols["var_mensal"] is not None:
                val = row.iloc[cols["var_mensal"]]
                if pd.notna(val) and str(val).strip() not in (".", "", "-"):
                    try:
                        record["variacao_mensal_pct"] = float(val) * 100  # já vem em decimal
                    except ValueError:
                        pass

            # Variação 12 meses
            if cols["var_12m"] is not None:
                val = row.iloc[cols["var_12m"]]
                if pd.notna(val) and str(val).strip() not in (".", "", "-"):
                    try:
                        record["variacao_12m_pct"] = float(val) * 100
                    except ValueError:
                        pass

            # Preço médio
            if cols["preco_medio"] is not None:
                val = row.iloc[cols["preco_medio"]]
                if pd.notna(val) and str(val).strip() not in (".", "", "-"):
                    try:
                        record["preco_medio_m2"] = float(val)
                    except ValueError:
                        pass

            # Só inclui se tiver pelo menos índice ou preço médio
            if "numero_indice" in record or "preco_medio_m2" in record:
                records.append(record)

    return records


def _normalizar_cidade(nome: str) -> str:
    """
    Normaliza nome da cidade vindo da aba do Excel.
    Em algumas versões do Excel da FIPE o encoding vem corrompido;
    mantemos um mapping defensivo pra casos conhecidos.
    """
    # Se o nome já estiver correto (UTF-8), retorna como está.
    # Se no futuro a FIPE mudar o encoding do arquivo, adicione mapping aqui.
    return nome


def _inferir_uf(cidade: str) -> str | None:
    """Heurística simples pra inferir UF a partir do nome da cidade."""
    mapping = {
        "São Paulo": "SP", "Barueri": "SP", "Campinas": "SP", "Diadema": "SP",
        "Guarujá": "SP", "Guarulhos": "SP", "Osasco": "SP", "Praia Grande": "SP",
        "Ribeirão Preto": "SP", "Santo André": "SP", "Santos": "SP",
        "São Bernardo do Campo": "SP", "São Caetano do Sul": "SP",
        "São José do Rio Preto": "SP", "São José dos Campos": "SP",
        "São Vicente": "SP",
        "Rio de Janeiro": "RJ", "Niterói": "RJ",
        "Belo Horizonte": "MG", "Betim": "MG", "Contagem": "MG",
        "Porto Alegre": "RS", "Canoas": "RS", "Caxias do Sul": "RS",
        "Novo Hamburgo": "RS", "Pelotas": "RS", "Santa Maria": "RS",
        "São Leopoldo": "RS",
        "Curitiba": "PR", "Londrina": "PR", "São José dos Pinhais": "PR",
        "Florianópolis": "SC", "Balneário Camboriú": "SC", "Blumenau": "SC",
        "Itajaí": "SC", "Itapema": "SC", "Joinville": "SC", "São José": "SC",
        "Vitória": "ES", "Vila Velha": "ES",
        "Brasília": "DF", "Goiânia": "GO", "Campo Grande": "MS",
        "Cuiabá": "MT", "Aracaju": "SE", "Fortaleza": "CE",
        "João Pessoa": "PB", "Maceió": "AL", "Natal": "RN",
        "Recife": "PE", "Salvador": "BA", "São Luís": "MA",
        "Teresina": "PI", "Jaboatão dos Guararapes": "PE",
        "Belém": "PA", "Manaus": "AM",
    }
    return mapping.get(cidade)


def upsert_records(supabase: Client, records: list[dict[str, Any]], dry_run: bool = False) -> int:
    """Faz upsert em batch na tabela fipezap_indices."""
    if not records:
        logger.warning("Nenhum registro para inserir.")
        return 0

    logger.info("Total de registros a upsertar: %d", len(records))

    if dry_run:
        logger.info("[DRY-RUN] Primeiros 3 registros:")
        for r in records[:3]:
            logger.info("  %s", r)
        return len(records)

    # Upsert em batches de 500 pra não estourar limites do PostgREST
    BATCH_SIZE = 500
    inserted = 0
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i : i + BATCH_SIZE]
        try:
            # Supabase Python client não tem upsert nativo em batch,
            # mas podemos usar RPC ou insert com on_conflict.
            # Aqui usamos a API REST direta via postgrest.
            resp = (
                supabase.table("fipezap_indices")
                .upsert(batch, on_conflict="cidade,tipo_indice,data_referencia")
                .execute()
            )
            inserted += len(batch)
            logger.info("Batch %d-%d OK", i, i + len(batch))
        except Exception as exc:
            logger.error("Erro no batch %d-%d: %s", i, i + len(batch), exc)
            raise

    logger.info("Upsert concluído: %d registros", inserted)
    return inserted


def main() -> int:
    parser = argparse.ArgumentParser(description="Loader FipeZap → Supabase")
    parser.add_argument("--file", type=Path, help="Path local do Excel FipeZap")
    parser.add_argument("--download", action="store_true", help="Baixa o Excel do site")
    parser.add_argument("--dry-run", action="store_true", help="Só mostra, não grava")
    parser.add_argument("--only-cidades", nargs="+", help="Processa só essas cidades")
    args = parser.parse_args()

    if not args.file and not args.download:
        logger.error("Use --file ou --download")
        return 1

    # 1. Obter arquivo
    if args.download:
        excel_path = download_excel()
    else:
        excel_path = args.file
        if not excel_path.exists():
            logger.error("Arquivo não encontrado: %s", excel_path)
            return 1

    # 2. Conectar Supabase
    if not args.dry_run:
        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            logger.error("SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY são obrigatórios")
            return 1
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    else:
        supabase = None  # type: ignore[assignment]

    # 3. Ler Excel
    logger.info("Lendo %s ...", excel_path)
    xl = pd.ExcelFile(str(excel_path))

    all_records: list[dict[str, Any]] = []
    for sheet_name in xl.sheet_names:
        if sheet_name in SKIP_SHEETS:
            logger.debug("Ignorando aba: %s", sheet_name)
            continue

        if args.only_cidades and sheet_name not in args.only_cidades:
            continue

        logger.info("Processando: %s", sheet_name)
        df = pd.read_excel(xl, sheet_name=sheet_name, header=None)
        records = parse_cidade_sheet(df, sheet_name)
        logger.info("  → %d registros extraídos", len(records))
        all_records.extend(records)

    # 4. Upsert
    logger.info("Total geral: %d registros", len(all_records))
    upsert_records(supabase, all_records, dry_run=args.dry_run)

    # 5. Cleanup (se foi download temporário)
    if args.download and not args.dry_run:
        excel_path.unlink(missing_ok=True)
        logger.info("Arquivo temporário removido: %s", excel_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
