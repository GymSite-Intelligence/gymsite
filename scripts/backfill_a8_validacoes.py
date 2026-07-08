#!/usr/bin/env python3
"""
Backfill do A8 validator para relatórios 'done' SEM linha em `validacoes`.

Contexto: o A8 roda dentro do A9 (a8_runner) e grava `validacoes`. Relatórios
legados (gerados antes dessa integração, ou onde o A8 estourou) ficaram sem a
linha → a auditoria de fidelidade os rejeita por falta do score do A8.

Este script reconstrói o input que o A8 espera (output_consolidado) a partir das
COLUNAS TOP-LEVEL de relatorio_outputs (nos legados o output_consolidado veio
vazio), roda o A8 real e persiste em `validacoes`.

Uso:
  python scripts/backfill_a8_validacoes.py --dry-run --limit 2   # roda, NÃO grava
  python scripts/backfill_a8_validacoes.py --persist --limit 27  # roda e GRAVA
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.cnpj_fitness_tools import _supabase_client
from tools.a8_runner import run_a8_validation, _persist_validacao_sync


def _reconstruir_oc(out: dict, cenarios: list, bairros_alt: list) -> dict:
    """output_consolidado-equivalente a partir das colunas de relatorio_outputs."""
    return {
        "veredito": out.get("veredito"),
        "score_bairro": out.get("score_bairro"),
        "scores": {
            "demografico": out.get("score_demografico"),
            "competitivo": out.get("score_concorrencia"),
            "viabilidade": out.get("score_viabilidade"),
        },
        "modelo_recomendado": out.get("modelo_recomendado"),
        "total_concorrentes_analisados": out.get("total_concorrentes_analisados"),
        "nivel_saturacao": out.get("nivel_saturacao"),
        "posicionamento_estrategico": out.get("posicionamento_estrategico"),
        "posicionamento_recomendado": out.get("posicionamento_recomendado"),
        "resumo_executivo": out.get("resumo_executivo"),
        "cobertura_redes_a0": out.get("cobertura_redes_a0") or {},
        "bairros_alternativos": bairros_alt or [],
        "viabilidade_3_cenarios": cenarios or [],
    }


def _ids_sem_validacao(sb, limite: int) -> list[dict]:
    done = sb.table("relatorios").select("id,org_id").eq("status", "done") \
        .is_("deleted_at", "null").order("created_at", desc=True).limit(300).execute().data or []
    faltantes = []
    for r in done:
        v = sb.table("validacoes").select("id").eq("relatorio_id", r["id"]).limit(1).execute().data
        if not v:
            faltantes.append(r)
        if len(faltantes) >= limite:
            break
    return faltantes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Backfill A8 em relatórios sem validacoes")
    ap.add_argument("--dry-run", action="store_true", help="Roda o A8 mas NÃO grava (default)")
    ap.add_argument("--persist", action="store_true", help="Grava as validacoes")
    ap.add_argument("--limit", type=int, default=2)
    args = ap.parse_args(argv)
    gravar = args.persist and not args.dry_run

    sb = _supabase_client()
    if sb is None:
        print("SUPABASE não configurado", file=sys.stderr); return 1

    faltantes = _ids_sem_validacao(sb, args.limit)
    print(f"[backfill] {len(faltantes)} relatório(s) sem validacoes (modo={'GRAVA' if gravar else 'dry-run'})",
          flush=True)

    ok = falhou = 0
    for r in faltantes:
        rid, org_id = r["id"], r.get("org_id")
        rel = sb.table("relatorios").select("markdown_completo").eq("id", rid).maybe_single().execute().data or {}
        out = sb.table("relatorio_outputs").select("*").eq("relatorio_id", rid).maybe_single().execute().data or {}
        cenarios = sb.table("cenarios_financeiros").select("*").eq("relatorio_id", rid).execute().data or []
        bairros = sb.table("bairros_alternativos").select("*").eq("relatorio_id", rid).execute().data or []

        md = rel.get("markdown_completo") or ""
        if not md:
            print(f"  {rid[:8]} SEM markdown_completo — pulo", flush=True); falhou += 1; continue

        oc = _reconstruir_oc(out, cenarios, bairros)
        try:
            validacao = run_a8_validation(md, oc, relatorio={"output_consolidado": oc, "cenarios": cenarios})
        except Exception as e:
            print(f"  {rid[:8]} A8 ERRO: {type(e).__name__}: {e}", flush=True); falhou += 1; continue

        if not validacao:
            print(f"  {rid[:8]} A8 retornou None — pulo", flush=True); falhou += 1; continue

        resumo = f"score={validacao.get('score_validacao')} status={validacao.get('status_validacao')} revisar={validacao.get('revisar_manual')}"
        if gravar:
            _persist_validacao_sync(rid, org_id or "", validacao)
            print(f"  {rid[:8]} GRAVADO · {resumo}", flush=True)
        else:
            print(f"  {rid[:8]} dry-run · {resumo}", flush=True)
        ok += 1

    print(f"\n[fim] processados_ok={ok} falhou={falhou} gravado={gravar}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
