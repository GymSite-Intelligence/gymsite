#!/usr/bin/env python3
"""
Regra de ouro (fase de testes) — snapshot QA pós-pipeline.

Equivalente ao checklist em docs/QA_RELATORIO_AUDIT.md + docs/QA_POS_PIPELINE_JOIN.sql.

Uso:
  python scripts/qa_regra_de_ouro.py <relatorio_uuid>
  python scripts/qa_regra_de_ouro.py b34b65d2-d8de-4a97-9a94-5e6b876de668
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


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


def run_qa(uuid: str) -> dict:
    import httpx

    base, headers = _sb_headers()

    def get_list(path: str) -> list:
        r = httpx.get(f"{base}/rest/v1/{path}", headers=headers, timeout=60)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else [data]

    rel = get_list(
        f"relatorios?id=eq.{uuid}&select=id,status,created_at,markdown_completo"
    )
    if not rel:
        raise ValueError(f"Relatório {uuid} não encontrado")
    rel = rel[0]

    inp = get_list(f"relatorio_inputs?relatorio_id=eq.{uuid}&select=cidade,bairro")
    out = get_list(
        f"relatorio_outputs?relatorio_id=eq.{uuid}"
        "&select=veredito,score_bairro,score_concorrencia,total_concorrentes_analisados"
    )
    comps = get_list(
        f"competidores?relatorio_id=eq.{uuid}"
        "&select=nome,place_id,horarios_pico,pico_semanal,rating_oficial,reviews"
        "&order=rating_oficial.desc"
    )
    cands = get_list(f"candidatos?relatorio_id=eq.{uuid}&select=posicao")

    out0 = out[0] if out else {}
    md = rel.get("markdown_completo") or ""

    qa_failures: list[str] = []
    if len(cands) == 0 and "Top" in md:
        qa_failures.append("candidatos vazio mas markdown cita Top 3")
    if len(comps) == 0 and ("academia" in md.lower() or "concorrent" in md.lower()):
        qa_failures.append("competidores vazio mas markdown lista academias")

    pico_ok: list[str] = []
    pico_missing: list[str] = []
    sem_place_id: list[str] = []
    for c in comps:
        nome = c.get("nome", "?")
        pid = (c.get("place_id") or "").strip()
        if not pid:
            sem_place_id.append(nome)
        hp = c.get("horarios_pico")
        has = False
        if isinstance(hp, dict) and hp:
            has = any(
                isinstance(v, dict) and any(int(x or 0) > 0 for x in v.values())
                for v in hp.values()
            )
        if has:
            pico_ok.append(nome)
        else:
            pico_missing.append(nome)

    report = {
        "relatorio_id": uuid,
        "status": rel.get("status"),
        "cidade": (inp[0] if inp else {}).get("cidade"),
        "bairro": (inp[0] if inp else {}).get("bairro"),
        "veredito": out0.get("veredito"),
        "score_bairro": out0.get("score_bairro"),
        "score_concorrencia": out0.get("score_concorrencia"),
        "total_concorrentes_analisados": out0.get("total_concorrentes_analisados"),
        "n_candidatos": len(cands),
        "n_competidores": len(comps),
        "pico_ok": pico_ok,
        "pico_missing": pico_missing,
        "sem_place_id": sem_place_id,
        "qa_failures": qa_failures,
        "qa_pass": len(qa_failures) == 0,
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="QA regra de ouro — relatório Supabase")
    parser.add_argument("uuid", help="UUID do relatório")
    args = parser.parse_args()

    report = run_qa(args.uuid)
    out_path = ROOT / "eval" / "runs" / f"{args.uuid}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nSalvo: {out_path}")
    if not report["qa_pass"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
