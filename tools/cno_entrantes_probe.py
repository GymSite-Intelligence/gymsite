#!/usr/bin/env python3
"""
Cruzamento amostral: entrantes CNPJ (90d) x CNO (obras) em Fortaleza.

Uso:
  python tools/cno_entrantes_probe.py --cno-dir "C:\\Users\\marce\\Downloads\\cno_extract"
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")
load_dotenv(_ROOT / "frontend" / ".env", override=False)

from tools.cnpj_fitness_tools import listar_entrantes_cnpj_fitness
from tools.financial_tools import ALUNOS_POR_M2


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def _norm_cep(cep: str) -> str:
    d = _digits(cep)
    return d[:8] if len(d) >= 8 else d


def _load_cno_index(cno_dir: Path, municipio: str = "1389") -> dict:
    """Índices por CNPJ e por CEP prefixo (5 dígitos)."""
    main = cno_dir / "cno.csv"
    areas_path = cno_dir / "cno_areas.csv"

    areas_by_cno: dict[str, list[dict]] = defaultdict(list)
    if areas_path.is_file():
        with open(areas_path, encoding="latin-1", errors="replace") as f:
            for row in csv.DictReader(f):
                areas_by_cno[row.get("CNO", "")].append(row)

    by_cnpj: dict[str, list[dict]] = defaultdict(list)
    by_cep5: dict[str, list[dict]] = defaultdict(list)

    with open(main, encoding="latin-1", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cod = (row.get("Código do municipio") or row.get("Codigo do municipio") or "").strip()
            if cod != municipio:
                continue
            cnpj = _digits(row.get("NI do responsável") or row.get("NI do responsavel") or "")
            cep = _norm_cep(row.get("CEP") or "")
            area_raw = row.get("Área total") or row.get("Area total") or "0"
            try:
                area = float(str(area_raw).replace(",", "."))
            except ValueError:
                area = 0.0

            destinos = []
            for a in areas_by_cno.get(row.get("CNO", ""), []):
                destinos.append(
                    {
                        "destinacao": a.get("Destinação") or a.get("Destinacao"),
                        "categoria": a.get("Categoria"),
                        "tipo_obra": a.get("Tipo de obra"),
                        "metragem": a.get("Metragem"),
                    }
                )

            rec = {
                "cno": row.get("CNO"),
                "nome": row.get("Nome"),
                "nome_empresarial": row.get("Nome empresarial"),
                "cnpj": cnpj,
                "cep": cep,
                "logradouro": row.get("Logradouro"),
                "numero": row.get("Número do logradouro") or row.get("Numero do logradouro"),
                "bairro": row.get("Bairro"),
                "area_total_m2": area,
                "situacao": row.get("Situação") or row.get("Situacao"),
                "data_inicio": row.get("Data de início") or row.get("Data de inicio"),
                "areas": destinos,
            }
            if len(cnpj) == 14:
                by_cnpj[cnpj].append(rec)
            if len(cep) >= 5:
                by_cep5[cep[:5]].append(rec)

    return {"by_cnpj": by_cnpj, "by_cep5": by_cep5}


def cruzar_entrantes_cno(
    *,
    cno_dir: Path,
    cidade: str = "Fortaleza",
    uf: str = "CE",
    dias: int = 90,
) -> dict:
    entrantes = listar_entrantes_cnpj_fitness(cidade, uf, dias, limit=50)
    idx = _load_cno_index(cno_dir)

    resultados = []
    match_cnpj = match_cep = sem_match = 0

    for e in entrantes.get("entrantes") or []:
        cnpj = _digits(e.get("cnpj", ""))
        cep5 = _norm_cep(e.get("cep") or "")[:5]
        obras = []
        metodo = None

        if cnpj and cnpj in idx["by_cnpj"]:
            obras = idx["by_cnpj"][cnpj]
            metodo = "cnpj_responsavel"
            match_cnpj += 1
        elif cep5 and cep5 in idx["by_cep5"]:
            obras = idx["by_cep5"][cep5][:5]
            metodo = "cep_prefixo_5"
            match_cep += 1
        else:
            sem_match += 1

        area_m2 = None
        capacidade = None
        if obras:
            areas = [o.get("area_total_m2") or 0 for o in obras]
            areas = [a for a in areas if a > 0]
            if areas:
                area_m2 = max(areas)
                capacidade = int(area_m2 * ALUNOS_POR_M2)

        resultados.append(
            {
                "cnpj": e.get("cnpj"),
                "nome_fantasia": e.get("nome_fantasia"),
                "segmento": e.get("segmento_operacao"),
                "data_abertura": e.get("data_abertura"),
                "cep": e.get("cep"),
                "match_metodo": metodo,
                "obras_encontradas": len(obras),
                "area_m2_cno": area_m2,
                "capacidade_estimada_alunos": capacidade,
                "obra_amostra": obras[0] if obras else None,
            }
        )

    com_area = sum(1 for r in resultados if r.get("area_m2_cno"))
    return {
        "cidade": cidade,
        "uf": uf,
        "total_entrantes": len(resultados),
        "match_por_cnpj": match_cnpj,
        "match_por_cep": match_cep,
        "sem_match_cno": sem_match,
        "com_area_m2_cno": com_area,
        "cruzamentos": resultados,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--cno-dir",
        default=r"C:\Users\marce\Downloads\cno_extract",
    )
    args = ap.parse_args()
    cno_dir = Path(args.cno_dir)
    if not (cno_dir / "cno.csv").is_file():
        print(f"ERRO: {cno_dir}/cno.csv não encontrado")
        return 1

    out = cruzar_entrantes_cno(cno_dir=cno_dir)
    import json

    print(json.dumps({k: out[k] for k in out if k != "cruzamentos"}, indent=2, ensure_ascii=False))
    print("\n--- Amostra com match ---")
    for r in out["cruzamentos"]:
        if r.get("match_metodo"):
            print(
                f"{r.get('nome_fantasia') or r.get('cnpj')}: "
                f"{r.get('match_metodo')} area={r.get('area_m2_cno')}m2 "
                f"cap~{r.get('capacidade_estimada_alunos')} alunos"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
