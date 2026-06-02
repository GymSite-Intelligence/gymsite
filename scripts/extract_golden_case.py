#!/usr/bin/env python3
"""
Extrai um relatório do Supabase por UUID e gera estrutura de Golden Case.

Uso:
  python scripts/extract_golden_case.py <uuid>
  python scripts/extract_golden_case.py <uuid> --output-dir eval/golden_dataset
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def _slug(text: str) -> str:
    s = unicodedata.normalize("NFKD", text or "")
    s = s.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")
    return s or "desconhecido"


def _sb_headers() -> tuple[str, dict[str, str]]:
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise SystemExit("SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY ausentes no .env")
    return url, {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }


def _get_one(url: str, headers: dict, path: str) -> dict | None:
    import httpx

    r = httpx.get(f"{url}/rest/v1/{path}", headers=headers, timeout=60)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    data = r.json()
    if isinstance(data, list):
        return data[0] if data else None
    return data


def _fetch_report_payload(uuid: str) -> dict:
    import httpx

    base, headers = _sb_headers()
    rel = _get_one(base, headers, f"relatorios?id=eq.{uuid}&select=*")
    if not rel:
        raise ValueError(f"Relatório {uuid} não encontrado no Supabase")

    rid = rel["id"]
    inp = _get_one(
        base,
        headers,
        f"relatorio_inputs?relatorio_id=eq.{rid}&select=*",
    )
    out = _get_one(
        base,
        headers,
        f"relatorio_outputs?relatorio_id=eq.{rid}&select=*",
    )
    if not inp:
        raise ValueError(f"relatorio_inputs ausente para {uuid}")
    if not out:
        raise ValueError(f"relatorio_outputs ausente para {uuid}")

    r_cand = httpx.get(
        f"{base}/rest/v1/candidatos?relatorio_id=eq.{rid}&select=*&order=posicao.asc&limit=10",
        headers=headers,
        timeout=60,
    )
    r_cand.raise_for_status()
    candidatos = r_cand.json() or []

    r_comp = httpx.get(
        f"{base}/rest/v1/competidores?relatorio_id=eq.{rid}&select=id",
        headers=headers,
        timeout=60,
    )
    r_comp.raise_for_status()
    competidores_count = len(r_comp.json() or [])

    input_canonico = {
        "cidade": inp.get("cidade") or "",
        "bairro": inp.get("bairro") or "",
        "uf": inp.get("uf") or "",
        "area_m2_min": inp.get("area_m2_min"),
        "area_m2_max": inp.get("area_m2_max"),
        "publico_alvo": inp.get("publico_alvo") or "25-40",
        "genero_alvo": inp.get("genero_alvo") or "misto",
        "tipo_negocio": inp.get("tipo_negocio") or "academia",
        "tamanho_preset": inp.get("tamanho_preset") or "m",
        "estacionamento_obrigatorio": inp.get("estacionamento_obrigatorio", True),
        "bairros_indicados": inp.get("bairros_indicados") or [],
    }

    output_consolidado = {
        **out,
        "scores_regionais": {
            "demografico": out.get("score_demografico"),
            "concorrencia": out.get("score_concorrencia"),
            "viabilidade": out.get("score_viabilidade"),
        },
        "alertas_financeiros": out.get("alertas") or [],
        "total_concorrentes_analisados": out.get("total_concorrentes_analisados")
        or competidores_count,
    }

    return {
        "id": rid,
        "header": rel,
        "input_canonico": input_canonico,
        "output_consolidado": output_consolidado,
        "candidatos": candidatos,
        "competidores_count": competidores_count,
    }


def _extract_cno_validation(payload: dict, input_canonico: dict) -> dict | None:
    """Ground truth CNO a partir do full_report (quando presente)."""
    oc = payload.get("output_consolidado") or {}
    obras_block = oc.get("obras_cno_em_curso") or {}
    if not isinstance(obras_block, dict) or not obras_block:
        return None

    bairro = (input_canonico.get("bairro") or "").strip()
    bairro_chave = bairro.lower().replace(" ", " ")

    mc = oc.get("market_context") or {}
    if isinstance(mc.get("market_context"), dict):
        mc = mc["market_context"]
    fatos = mc.get("fatos_parque_cnpj") or mc.get("fatos_mercado") or mc.get("dados_parque_cnpj") or {}
    cruz = {}
    if isinstance(fatos, dict):
        cruz = fatos.get("cruzamento_cno") or {}

    obras_list = obras_block.get("obras") or []
    no_bairro = [
        o
        for o in obras_list
        if bairro_chave
        and bairro_chave in (o.get("bairro_chave") or o.get("bairro") or "").lower()
    ]

    bench = obras_block.get("benchmark_tempo_obra") or {}
    dpm2 = (bench.get("metricas") or {}).get("dias_por_m2_mediana")

    out: dict = {
        "required": True,
        "expected_status": obras_block.get("status", "ok"),
        "bairro_chave": bairro_chave,
        "total_obras_em_curso_municipio": obras_block.get("total_obras_em_curso")
        or len(obras_list),
        "total_obras_em_curso_bairro": len(no_bairro),
        "obras_count_tolerance": 2,
        "benchmark_dias_por_m2_tolerance": 0.05,
    }
    if dpm2 is not None:
        out["benchmark_dias_por_m2_mediana"] = dpm2
    if no_bairro:
        out["obras_em_curso_bairro"] = [
            {
                "cno": o.get("cno"),
                "area_m2": o.get("area_m2"),
                "nome_obra": o.get("nome_obra"),
            }
            for o in no_bairro
        ]
    resumo = cruz.get("resumo_match")
    if isinstance(resumo, dict) and resumo:
        out["cruzamento_resumo_match"] = resumo
    refs = cruz.get("obras_referencia") or []
    for ref in refs:
        rb = (ref.get("bairro") or "").lower()
        if bairro_chave and bairro_chave in rb:
            out["obra_referencia_encerrada_bairro"] = ref
            break
    return out


def _merge_preserved_golden_fields(new_case: dict, existing_path: Path) -> None:
    """Preserva curadoria ao re-extrair (cno_validation, approved, etc.)."""
    if not existing_path.is_file():
        return
    try:
        old = json.loads(existing_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    for key in (
        "approved",
        "cno_validation",
        "curator_notes",
        "structural_validation",
        "financial_validation",
        "positioning_validation",
    ):
        if key in old:
            new_case[key] = old[key]
    if old.get("case_id"):
        new_case["case_id"] = old["case_id"]


def extract_golden_case(
    uuid: str,
    output_dir: Path,
    *,
    target_case_dir: Path | None = None,
) -> dict:
    payload = _fetch_report_payload(uuid)
    rel = payload["header"]
    input_canonico = payload["input_canonico"]
    output_consolidado = payload["output_consolidado"]

    veredito = output_consolidado.get("veredito", "DESCONHECIDO")
    score_top1 = output_consolidado.get("score_top1_candidato")
    modelo = output_consolidado.get("modelo_recomendado") or "DESCONHECIDO"

    created = (rel.get("created_at") or rel.get("data_execucao") or "")[:10]
    data_str = created.replace("-", "") if created else "00000000"
    case_id = "_".join(
        [
            _slug(input_canonico.get("cidade", "cidade")),
            _slug(input_canonico.get("bairro", "bairro")),
            data_str,
        ]
    )

    golden_case = {
        "case_id": case_id,
        "uuid": uuid,
        "adk_run_id": rel.get("adk_run_id"),
        "created_at": rel.get("created_at"),
        "data_execucao": rel.get("data_execucao"),
        "pipeline_version": rel.get("schema_version", "1.5"),
        "status": rel.get("status"),
        "input_canonico": input_canonico,
        "expected_veredito": veredito,
        "expected_score_top1": score_top1,
        "expected_modelo_recomendado": modelo,
        "expected_nivel_saturacao": output_consolidado.get("nivel_saturacao"),
        "expected_score_bairro": output_consolidado.get("score_bairro"),
        "candidatos_count": len(payload.get("candidatos") or []),
        "competidores_count": payload.get("competidores_count"),
        "critical_fields": [
            "veredito",
            "score_top1_candidato",
            "modelo_recomendado",
            "nivel_saturacao",
        ],
        "tolerance_fields": {
            "score_top1_candidato": 0.5,
            "aluguel_mensal": 0.10,
        },
        "curator_notes": "",
        "approved": False,
    }

    cno_val = _extract_cno_validation(payload, input_canonico)
    if cno_val:
        golden_case["cno_validation"] = cno_val

    if target_case_dir is not None:
        case_dir = target_case_dir.resolve()
        case_dir.mkdir(parents=True, exist_ok=True)
        existing_expected = case_dir / "expected_output.json"
        _merge_preserved_golden_fields(golden_case, existing_expected)
        if existing_expected.is_file():
            try:
                prev = json.loads(existing_expected.read_text(encoding="utf-8"))
                golden_case["case_id"] = prev.get("case_id") or golden_case["case_id"]
            except json.JSONDecodeError:
                pass
    else:
        case_dir = output_dir / case_id
        case_dir.mkdir(parents=True, exist_ok=True)

    (case_dir / "input.json").write_text(
        json.dumps(input_canonico, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    (case_dir / "expected_output.json").write_text(
        json.dumps(golden_case, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    (case_dir / "full_report.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    notes_md = f"""# Golden Case: {case_id}

## Identificação
- **UUID:** `{uuid}`
- **ADK Run ID:** `{rel.get("adk_run_id", "N/A")}`
- **Data Criação:** {rel.get("created_at", "N/A")}
- **Pipeline Version:** {golden_case["pipeline_version"]}
- **Status:** {rel.get("status", "N/A")}

## Input
- **Cidade:** {input_canonico.get("cidade", "?")}
- **Bairro:** {input_canonico.get("bairro", "?")}
- **UF:** {input_canonico.get("uf", "?")}
- **Área:** {input_canonico.get("area_m2_min")}-{input_canonico.get("area_m2_max")} m²
- **Público:** {input_canonico.get("publico_alvo", "?")}
- **Tipo Negócio:** {input_canonico.get("tipo_negocio", "?")}
- **Tamanho Preset:** {input_canonico.get("tamanho_preset", "?")}
- **Gênero Alvo:** {input_canonico.get("genero_alvo", "?")}

## Output Esperado (ground truth Supabase)
- **Veredito:** {veredito}
- **Score Top1:** {score_top1}
- **Score Bairro:** {output_consolidado.get("score_bairro")}
- **Modelo Recomendado:** {modelo}
- **Saturação:** {output_consolidado.get("nivel_saturacao")}
- **Candidatos (DB):** {golden_case["candidatos_count"]}
- **Concorrentes (DB):** {golden_case["competidores_count"]}

## Campos Críticos (devem bater exatamente)
{chr(10).join(f"- `{f}`" for f in golden_case["critical_fields"])}

## Campos com Tolerância
{chr(10).join(f"- `{k}`: ±{v * 100:.0f}%" for k, v in golden_case["tolerance_fields"].items())}

## Notas do Curador
<!-- Preencha: por que este caso é ground truth -->


## Aprovação
- [ ] Veredito correto
- [ ] Score dentro da faixa esperada
- [ ] Modelo recomendado faz sentido
- [ ] Campos críticos validados
- [ ] Notas do curador preenchidas
"""
    (case_dir / "notes.md").write_text(notes_md, encoding="utf-8")

    return golden_case


def main() -> int:
    parser = argparse.ArgumentParser(description="Extrai Golden Case do Supabase")
    parser.add_argument("uuid", help="UUID do relatório no Supabase")
    parser.add_argument(
        "--output-dir",
        default="eval/golden_dataset",
        help="Diretório de saída (default: eval/golden_dataset)",
    )
    parser.add_argument(
        "--target-dir",
        help="Pasta do caso existente (preserva case_id e curadoria)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = Path(args.target_dir) if args.target_dir else None

    print(f"Extraindo golden case: {args.uuid}")
    case = extract_golden_case(args.uuid, output_dir, target_case_dir=target)

    print(f"OK Caso extraído: {case['case_id']}")
    print(f"   Veredito: {case['expected_veredito']}")
    print(f"   Score Top1: {case['expected_score_top1']}")
    print(f"   Modelo: {case['expected_modelo_recomendado']}")
    print(f"   Diretório: {output_dir / case['case_id']}")
    print(f"\nPróximo passo: revise {output_dir / case['case_id'] / 'notes.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
