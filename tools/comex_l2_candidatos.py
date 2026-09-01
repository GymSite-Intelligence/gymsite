"""L2 Company Intel lite — candidatos CNPJ por cidades do gabarito 9506.

Fonte: BigQuery basedosdados.br_me_cnpj (RFB via Base dos Dados).
Nao afirma que o CNPJ importou NCM 9506 — so ranqueia candidatos legais.

Uso:
  .venv/Scripts/python.exe tools/comex_l2_candidatos.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.company_intel_recall import normalize_importer_name, recall_at_k

load_dotenv(_ROOT / ".env")

GOLDEN_ROLLUP = _ROOT / "docs" / "comex" / "golden" / "importadores_9506_rollup.json"
OUT_DIR = _ROOT / "docs" / "comex" / "l2"
OUT_CANDIDATES = OUT_DIR / "candidatos_cidades_golden.json"
OUT_RECALL = OUT_DIR / "recall_vs_golden.json"

# IBGE 7-digit (basedosdados.br_bd_diretorios_brasil.municipio)
CITY_IBGE = {
    "ITAJAI": "4208203",
    "JOINVILLE": "4209102",
    "PALHOCA": "4211900",
    "BARUERI": "3505708",
    "SAO PAULO": "3550308",
}

# CNAEs uteis p/ import/atacado fitness / esportes / logistica comex
CNAES = [
    "4641903",  # atacado equipamentos/artigos (STONE)
    "4763601",
    "4763602",  # varejo artigos esportivos
    "4763603",
    "4691500",  # atacado nao especializado
    "4689301",
    "4689399",
    "4649499",
    "4644301",
    "5250803",
    "5250804",  # logistica / agentes
    "5211799",
    "5212501",
    "5229001",
    "5229099",
]

# Tokens na razao social (OR)
NAME_REGEX = (
    r"IMPORT|EXPORT|FITNESS|ESPORT|SPORT|GINAST|ATACAD|"
    r"TRADING|INTERNACIONAL|COMERCIO INTERNAC|"
    r"EQUIPAMENT|ACADEM|NATACAO|BIOSWIM|LIFE FITNESS"
)

# Peso cidade: sedes do golden SC > SP diluido
CITY_WEIGHT = {
    "4208203": 30,  # Itajai
    "4209102": 25,  # Joinville
    "4211900": 20,  # Palhoca
    "3505708": 10,  # Barueri
    "3550308": 5,  # Sao Paulo
}


def _client() -> bigquery.Client:
    project = (os.getenv("GOOGLE_CLOUD_PROJECT") or "").strip()
    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT ausente no .env")
    return bigquery.Client(project=project)


def latest_partition(client: bigquery.Client) -> tuple[int, int]:
    q = """
    SELECT ano, mes
    FROM `basedosdados.br_me_cnpj.estabelecimentos`
    WHERE ano >= 2024
    GROUP BY ano, mes
    ORDER BY ano DESC, mes DESC
    LIMIT 1
    """
    row = next(iter(client.query(q).result()))
    return int(row.ano), int(row.mes)


def fetch_candidates(
    client: bigquery.Client,
    ano: int,
    mes: int,
    golden_names: list[str],
) -> list[dict]:
    city_ids = list(CITY_IBGE.values())
    cnae_list = ", ".join(f"'{c}'" for c in CNAES)
    cities_sql = ", ".join(f"'{c}'" for c in city_ids)
    # Exact razao boost for gabarito (ex.: IDEAL COMERCIAL sem token IMPORT)
    golden_sql_parts = []
    for n in golden_names:
        esc = n.replace("\\", "\\\\").replace("'", "\\'")
        golden_sql_parts.append(f"UPPER(emp.razao_social) LIKE UPPER('{esc}')")
        # tolerate S/A vs S A
        alt = re.sub(r"\bS A\b", "S/A", n, flags=re.I)
        if alt != n:
            esc2 = alt.replace("\\", "\\\\").replace("'", "\\'")
            golden_sql_parts.append(f"UPPER(emp.razao_social) LIKE UPPER('{esc2}')")
    golden_or = " OR ".join(golden_sql_parts) if golden_sql_parts else "FALSE"

    q = f"""
    WITH base AS (
      SELECT
        e.cnpj,
        e.cnpj_basico,
        e.nome_fantasia,
        emp.razao_social,
        e.cnae_fiscal_principal AS cnae,
        e.id_municipio,
        e.sigla_uf,
        emp.capital_social,
        emp.porte,
        e.data_inicio_atividade,
        e.identificador_matriz_filial,
        e.cnpj_ordem
      FROM `basedosdados.br_me_cnpj.estabelecimentos` e
      JOIN `basedosdados.br_me_cnpj.empresas` emp
        ON e.cnpj_basico = emp.cnpj_basico
       AND e.ano = emp.ano AND e.mes = emp.mes
      WHERE e.ano = @ano AND e.mes = @mes
        AND e.situacao_cadastral = '2'
        AND e.id_municipio IN ({cities_sql})
        AND emp.razao_social IS NOT NULL
        AND (
          ({golden_or})
          OR (
            e.id_municipio IN ('4208203','4209102','4211900')
            AND (
              e.cnae_fiscal_principal IN ({cnae_list})
              OR STARTS_WITH(e.cnae_fiscal_principal, '464')
              OR REGEXP_CONTAINS(UPPER(emp.razao_social), r'{NAME_REGEX}')
            )
          )
          OR (
            e.id_municipio IN ('3505708','3550308')
            AND REGEXP_CONTAINS(
              UPPER(emp.razao_social),
              r'IMPORT|EXPORT|FITNESS|ESPORT|SPORT|GINAST|LIFE FITNESS|TRADING|INTERNACIONAL'
            )
          )
        )
    )
    SELECT * EXCEPT(identificador_matriz_filial, cnpj_ordem)
    FROM base
    QUALIFY ROW_NUMBER() OVER (
      PARTITION BY cnpj_basico
      ORDER BY
        CASE WHEN CAST(identificador_matriz_filial AS STRING) IN ('1', '01') THEN 0 ELSE 1 END,
        CASE WHEN cnpj_ordem = '0001' THEN 0 ELSE 1 END,
        cnpj
    ) = 1
    """
    job = client.query(
        q,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("ano", "INT64", ano),
                bigquery.ScalarQueryParameter("mes", "INT64", mes),
            ]
        ),
    )
    rows = []
    for r in job.result():
        rows.append(
            {
                "cnpj": r.cnpj,
                "cnpj_basico": r.cnpj_basico,
                "razao_social": r.razao_social,
                "nome_fantasia": r.nome_fantasia,
                "cnae": r.cnae,
                "id_municipio": r.id_municipio,
                "uf": r.sigla_uf,
                "capital_social": float(r.capital_social or 0),
                "porte": r.porte,
                "data_inicio_atividade": str(r.data_inicio_atividade or ""),
            }
        )
    return rows


def _city_name(id_municipio: str) -> str:
    for name, mid in CITY_IBGE.items():
        if mid == id_municipio:
            return name
    return id_municipio


def score_row(row: dict, golden_norms: set[str]) -> dict:
    razao = row["razao_social"] or ""
    norm = normalize_importer_name(razao)
    score = float(CITY_WEIGHT.get(row["id_municipio"], 0))
    reasons: list[str] = [f"cidade:{_city_name(row['id_municipio'])}"]

    if row["cnae"] in CNAES:
        score += 25
        reasons.append(f"cnae:{row['cnae']}")

    upper = razao.upper()
    for tok, pts in (
        ("IMPORT", 20),
        ("EXPORT", 12),
        ("FITNESS", 18),
        ("ESPORT", 15),
        ("SPORT", 12),
        ("GINAST", 15),
        ("ATACAD", 10),
        ("TRADING", 12),
        ("INTERNACIONAL", 10),
        ("LIFE FITNESS", 25),
    ):
        if tok in upper:
            score += pts
            reasons.append(f"token:{tok}")

    # exact / near match with golden
    if norm in golden_norms:
        score += 100
        reasons.append("match_golden_exato")
    else:
        for g in golden_norms:
            # token overlap
            g_toks = set(g.split()) - {"LTDA", "SA", "E", "DE", "DA", "DO", "COMERCIO"}
            n_toks = set(norm.split())
            inter = g_toks & n_toks
            if len(inter) >= 2:
                score += 15 + 5 * len(inter)
                reasons.append(f"overlap:{','.join(sorted(inter)[:4])}")
                break

    if row["capital_social"] >= 100_000:
        score += 5
        reasons.append("capital>=100k")
    if row["capital_social"] >= 1_000_000:
        score += 5
        reasons.append("capital>=1M")

    out = dict(row)
    out["cidade"] = _city_name(row["id_municipio"])
    out["razao_norm"] = norm
    out["score"] = round(score, 1)
    out["reasons"] = reasons
    return out


def main() -> None:
    golden = json.loads(GOLDEN_ROLLUP.read_text(encoding="utf-8"))
    golden_names = [r["importador"] for r in golden]
    golden_norms = {normalize_importer_name(n) for n in golden_names}

    client = _client()
    ano, mes = latest_partition(client)
    print(f"[l2] partition {ano}-{mes:02d}", flush=True)

    raw = fetch_candidates(client, ano, mes, golden_names)
    print(f"[l2] raw candidates (dedup basico): {len(raw)}", flush=True)

    scored = [score_row(r, golden_norms) for r in raw]
    scored.sort(key=lambda x: (-x["score"], x["razao_social"]))

    # keep top 500 for artifact; recall uses ordered list
    top = scored[:500]
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "meta": {
            "fonte": "basedosdados.br_me_cnpj",
            "partition": {"ano": ano, "mes": mes},
            "cidades_ibge": CITY_IBGE,
            "n_raw": len(raw),
            "n_top": len(top),
            "carimbo": (
                f"candidatos ATIVOS · municipios do gabarito 9506 · "
                f"RFB via Base dos Dados {ano}-{mes:02d} · "
                "NAO e comprovacao de importacao NCM"
            ),
        },
        "candidatos": top,
    }
    OUT_CANDIDATES.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    ordered_names = [c["razao_social"] for c in scored]
    recall50 = recall_at_k(golden_names, ordered_names, k=50)
    recall100 = recall_at_k(golden_names, ordered_names, k=100)
    recall500 = recall_at_k(golden_names, ordered_names, k=500)
    recall_all = recall_at_k(golden_names, ordered_names, k=None)

    scored_by_norm = {c["razao_norm"]: c for c in scored}
    found_map = []
    for g in golden:
        gn = normalize_importer_name(g["importador"])
        hit = scored_by_norm.get(gn)
        found_map.append(
            {
                "importador": g["importador"],
                "total_teus": g["total_teus"],
                "cidades_golden": g["cidades"],
                "found": bool(hit),
                "rank": next(
                    (i + 1 for i, c in enumerate(scored) if c["razao_norm"] == gn),
                    None,
                ),
                "cnpj": (hit or {}).get("cnpj"),
                "score": (hit or {}).get("score"),
                "cidade_rfb": (hit or {}).get("cidade"),
                "cnae": (hit or {}).get("cnae"),
            }
        )

    recall_payload = {
        "meta": payload["meta"],
        "recall_at_50": recall50,
        "recall_at_100": recall100,
        "recall_at_500": recall500,
        "recall_all_candidates": recall_all,
        "por_importador": found_map,
        "top20": [
            {
                "rank": i + 1,
                "score": c["score"],
                "razao_social": c["razao_social"],
                "cidade": c["cidade"],
                "cnae": c["cnae"],
                "cnpj": c["cnpj"],
            }
            for i, c in enumerate(top[:20])
        ],
    }
    OUT_RECALL.write_text(
        json.dumps(recall_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        f"[l2] Recall@50={recall50['recall']:.1%} "
        f"hits={len(recall50['hits'])}/{recall50['n_golden']}",
        flush=True,
    )
    print(
        f"[l2] Recall@all={recall_all['recall']:.1%} "
        f"hits={len(recall_all['hits'])}/{recall_all['n_golden']}",
        flush=True,
    )
    print("[l2] misses:", recall_all["misses"], flush=True)
    print("[l2] wrote", OUT_CANDIDATES, flush=True)
    print("[l2] wrote", OUT_RECALL, flush=True)


if __name__ == "__main__":
    main()
